# Project Architecture

## Project overview

`coros-garmin-auto-sync` is a personal-automation Telegram bot that bridges two fitness platforms: it pulls activity data from a Coros sports watch (via Coros' internal Team EU API) and uploads/syncs those activities into Garmin Connect. Users interact entirely through Telegram commands and inline keyboards (e.g. "Sync latest", "Sync daily", date-picker calendar) — there is no web UI. The bot is multi-user: each allow-listed Telegram user links their own Coros and Garmin accounts via a `/register` conversation, and all credentials/sessions are stored per user in Redis. It is a small, single-maintainer project run both locally (for development) and deployed to Render.com.

## Technology stack

- **Language:** Python 3.11 (pinned via Pipfile, `python_full_version = "3.11.10"`)
- **Bot framework:** `aiogram` 3.x — async Telegram bot framework; this is the primary interface of the app (long-polling, FSM states for the date-picker flow)
- **Web framework:** `cherrypy` — a minimal embedded web server (`web.py`) exposing a single `/` health-check route, intended to satisfy Render's "web service" port-binding requirement
- **Fitness API clients:**
  - `garmin-connect==0.0.9.4` (installed from a custom TestPyPI index) + its dependency `garth` — Garmin Connect authentication and activity upload
  - Coros integration is hand-rolled: raw `urllib3.PoolManager` HTTP calls against Coros' Team EU API (no SDK)
- **Data/config:** `pydantic` 2.9.2 + `pydantic-settings` 2.5.2 for typed, env-prefixed settings (`CorosConfiguration`, `TelegramBotConfiguration`, `RedisConfiguration`); `python-dotenv` for local `.env` loading
- **Caching client:** `redis` (Python client, v6.x resolved)
- **Dev tooling:** `black`, `mypy`, `pre-commit` (declared oddly under `[packages]` rather than `[dev-packages]`, which is empty)
- **Package management:** Pipenv (`Pipfile` / `Pipfile.lock`), no `pyproject.toml`
- **No test framework** is present — zero automated test coverage today (no pytest/tox, no test files)

## Data layer

- **Redis is the only datastore.** There is no relational or document database, and no ORM.
- Redis stores per-user profiles, sessions, and caches, accessed through a small custom repository abstraction:
  - `core/repositories/base_repository.py` — generic `Repository` ABC (`get`/`set`) and `RedisRepository`
  - `users/repository.py` — `UserRedisRepository`: user profiles and Garmin OAuth tokens
  - `coros/repositories/redis_repository.py` — `CorosRedisRepository`: Coros access-token cache (TTL = 30 min) and latest-activity payloads
- Redis key model (`tg_id` = Telegram user id):
  - `user:{tg_id}:profile` — JSON: coros_email, coros_password_md5, garmin_email, created_at
  - `user:{tg_id}:garmin_oauth` — JSON: garth OAuth1/OAuth2 tokens (long-lived Garmin session)
  - `coros:access_token:{coros_email}` — Coros bearer token, 30-min TTL
  - `coros:latest_activity:{coros_email}` — last-synced activity payload
  - aiogram FSM state (registration/date-picker flows) via `RedisStorage`
- No migrations, no schema versioning — Redis keys/values are managed ad hoc in code.
- Configuration: `core/configuration.py`'s `RedisConfiguration` supports either discrete `REDIS_HOST`/`REDIS_PORT`/`REDIS_DB` env vars (local dev) or a single `REDIS_URL` (used by Render's managed Redis add-on in production).

## Deployment targets

- **Local development:** run directly with `python app.py`; `docker-compose.yml` spins up only a local Redis container (`redis:7.0.8`, host port 6380) for this purpose — there is no app service in the compose file.
- **Render.com (dev/prod combined):** deployed via `render.yaml`:
  - `auth-sync-service-dev` — a Docker-runtime web service (free plan, Frankfurt region), built from `deploy/Dockerfile`, tracking the `dev` branch
  - `redis` — a managed Render Redis add-on (free plan, `noeviction` policy), wired to the web service via `REDIS_URL`
  - There is no separate production service/branch today — the `dev` Render deployment functions as the live environment.
- **Dockerfile** (`deploy/Dockerfile`): based on `python:3.11-slim`; installs `pipenv` and runs `pipenv install --system --deploy`; entrypoint is `python app.py`.
- **Known issue to be aware of when touching `app.py`:** `run_bot()` blocks (it calls `asyncio.run(...)` internally for aiogram long-polling), so the subsequent `run_web()` call is only reached after the bot stops — meaning the CherryPy health-check server is effectively dead code in the current synchronous flow, despite Render deploying this as a `web` service that expects something bound to a port. Any change to concurrency here (e.g. running bot + web server together) should account for this.
- **CI:** `.github/workflows /mypy.yml` runs a mypy check on push for `*.py` changes — note the directory name has a trailing space (`"workflows "` not `"workflows"`), which means GitHub Actions likely does not recognize/run this workflow. Flag this if touching CI config.

## Service boundaries

Everything lives in one deployable process/repo — this is a modular monolith, not multiple services. Module boundaries by top-level package:

- **`core/`** — shared infrastructure with no product-specific logic: settings loading (`configuration.py`), logging setup (`logger.py`), the generic `CamelModel` pydantic base (`schemas.py`), and the generic Redis repository abstraction (`repositories/`).
- **`coros/`** — all Coros API integration: config (`configuration.py`), API URL templates and enums (`constants.py`), Pydantic models for Coros responses (`models/`), the Redis-backed token/activity cache (`repositories/`), and the service layer (`services/`: `AuthService` for login + token caching, `ActivityService` for listing/downloading activities, `BaseService` holding shared config/HTTP client).
- **Autosync worker** (`telegram/autosync.py`) — an asyncio background task started alongside bot polling. Every `TELEGRAM_AUTOSYNC_INTERVAL` seconds (default 600) it iterates all registered profiles with `autosync=True`, detects a new latest Coros activity (baseline stored under `coros:latest_activity:{email}`), uploads the last two days of activities to Garmin (duplicates are skipped by Garmin), and notifies the user in Telegram. Toggled per user with `/autosync`. Auto-disables (with a notification) on Coros auth failure or expired Garmin session. Note: on Render's free tier the service sleeps after 15 min without inbound HTTP traffic — an external keep-alive ping to the CherryPy `/` endpoint (e.g. UptimeRobot every 5 min) is required for autosync to run continuously.
- **`telegram/`** — the bot/UI layer built on aiogram: bot bootstrap (`app.py`), config (`configuration.py`), keyboards and calendar UI (`keyboards.py`, `calendar/`), FSM states (`states/`), and `handlers/` (organized by feature: `sport/` for the Coros→Garmin sync flows — latest activity, daily get, daily sync — plus a catch-all `base.py` and a stubbed `todo.py`). `telegram/utils.py` contains the cross-cutting glue that actually calls both the Coros services and the Garmin Connect client to perform a sync.
- **Web (`web.py`)** — a standalone CherryPy health-check endpoint, not integrated with the bot's async flow (see the known issue above).

Communication between modules is direct Python function/class calls (imports) — no internal HTTP or message-queue boundaries. `telegram/` depends on `coros/` (to fetch activities) and on the external `garmin-connect` package (to upload them); `coros/` depends on `core/` for config and Redis access.

## External integrations

- **Coros Team EU API** (`https://teameuapi.coros.com`) — undocumented/internal API, accessed via raw `urllib3` calls in `coros/services/`. Auth is email + MD5-hashed password (`CorosConfiguration.hashed_password`), yielding a bearer token cached in Redis for ~30 minutes.
- **Garmin Connect** — accessed via the third-party `garmin-connect` PyPI package (installed from TestPyPI, pinned to `0.0.9.4`) and its `garth` auth dependency. Used to upload activity files and read back the resulting activity list. Handles duplicate-activity conflicts by catching `GarthHTTPError`.
- **Telegram Bot API** — via `aiogram`, using a bot token (`TELEGRAM_TOKEN`) for long-polling.

These three are the complete set of external dependencies — confirmed, no others.

## Coding conventions

- Config is always defined as a `pydantic-settings` `BaseSettings` subclass with an explicit `env_prefix` (`coros_`, `telegram_`, `redis_`), loaded from a local `.env` via `python-dotenv`/`find_dotenv` in development, and from real environment variables in Render.
- API-facing/external-shape schemas subclass `core.schemas.CamelModel` (auto-converts snake_case Python fields to camelCase, matching JSON payload conventions from Coros/Garmin); internal-only models are plain `pydantic.BaseModel`.
- Data access goes through the `Repository` ABC pattern (`get`/`set`) rather than calling the Redis client directly; domain-specific repositories (e.g. `CorosRedisRepository`) extend the generic one with named methods rather than exposing raw key strings to callers.
- Telegram handlers are organized by feature area under `telegram/handlers/`, with aiogram `Router` objects per feature (e.g. `sport_router`) registered centrally in `telegram/app.py`.
- `black` and `mypy` are configured (pre-commit + a — currently likely broken — CI workflow); follow their formatting/typing conventions when editing.
- No test suite exists yet; there is no established test convention to follow. If adding tests, a framework/pattern will need to be chosen from scratch.

## Security posture

This is a small multi-user personal project — there are no compliance frameworks, data residency requirements, or formal auth standards in scope. Baseline hygiene to maintain:

- Bot-level secrets (`TELEGRAM_TOKEN`, Redis connection info) live only in `.env` locally (never committed — `example.env` is the template with blank values) and as Render environment variables in production. Never hardcode or log credential values.
- **Access control:** only Telegram user ids listed in `TELEGRAM_ALLOWED_USER_IDS` can register or use sport commands. Enforced in `/register` and in `UserContextMiddleware` (`telegram/middlewares/user_context.py`).
- **Per-user credentials live in Redis, not env vars.** For Coros only the MD5 hash of the password is stored (it's what the Coros API accepts — the hash is password-equivalent for this API, treat it as a secret). The Garmin password is never stored: it is used once during `/register` to obtain garth OAuth tokens, which are then persisted per user.
- During registration, messages containing passwords are deleted from the chat immediately after processing; plaintext passwords never enter FSM storage or logs.
- Data in Redis is stored unencrypted — a consciously accepted risk for this project's threat model (private Render Redis, allow-listed users). If that changes, add an encryption layer (e.g. Fernet) in `users/repository.py`.
- Garmin accounts with MFA/2FA are not supported (registration fails with a clear message).
- No regulatory/compliance constraints apply. Standard practice — don't commit secrets, don't log credentials or tokens, keep `.env` out of version control — is sufficient.
