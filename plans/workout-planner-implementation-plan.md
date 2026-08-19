# AI-планировщик тренировок для Coros (текст → структурированная тренировка → часы)

## Context

Пользователь хочет создавать тренировки текстовым описанием (например: "10 мин разминка, 4×400м в темпе с 2 мин отдыха, 10 мин заминка, на завтра") и получать их на Coros-часах — как это делает сторонний сервис Tredict, но бесплатно и внутри своего бота. Сам Coros не даёт API для записи тренировок — эндпоинт недокументирован, пользователь реверс-инжинирит его вручную через DevTools на `traininghub.coros.com` и уже прислал два реальных payload'а:

- `POST /training/program/calculate` — считает черновик тренировки (duration/distance/trainingLoad и т.п. из `exercises[]`).
- `POST /training/schedule/update` — реально сохраняет тренировку в расписание на дату (`entities[].happenDay`, формат `YYYYMMDD`) и связывает её с "обогащённым" объектом программы.

Фича должна жить **отдельным модулем**, изолированным от текущего стабильного Coros→Garmin sync-flow — если недокументированный write-эндпоинт сломается или Coros поменяет схему, это не должно задевать существующую синхронизацию активностей.

## Architecture decision

Новый top-level пакет **`workout_planner/`** (по аналогии с `coros/`, `users/`, `core/`). Он:

- **Переиспользует** `coros.configuration.CorosConfiguration` и `coros.services.auth.AuthService` для получения/кеширования access-token (не дублирует логин) — это уже работающий, протестированный механизм.
- **Не модифицирует** ни один существующий файл в `coros/` (никаких новых ключей в `coros/constants.py::API_URLS`, никаких правок в `ActivityService`). Свои URL-шаблоны и enum'ы держит в собственном `workout_planner/constants.py`.
- Новый Coros-сервис (`CorosWorkoutService`) наследуется от `coros.services.base.BaseService`, но **переопределяет** `get_headers()`/`get_url()` под свои нужды — так же, как это уже делает `ActivityService`. Важно: реальный код показывает, что токен передаётся не как `Authorization: Bearer`, а как заголовок `accesstoken` (см. `ActivityService.get_headers`, `coros/services/activity.py:44-53`) — этот же паттерн используем здесь, а не предположение про Bearer.
- Черновик тренировки на этапе "предпросмотр → подтверждение" хранится **в FSM-состоянии aiogram** (`state.update_data(...)`), а не в отдельном Redis-репозитории — FSM storage уже Redis-backed, отдельная сущность не нужна (упрощение).
- LLM-вызов к OpenRouter делается через `requests` (уже есть в `Pipfile`, `openai`/`anthropic` SDK не нужен — OpenRouter API OpenAI-совместимый), синхронно, обёрнуто в `asyncio.to_thread(...)` — как остальные блокирующие вызовы в проекте (`asyncio.to_thread(AuthService(...).get_or_set_access_token)` в `latest_activity_handlers.py:55-86`).

## ⚠️ Prerequisite — доразведка API (совместно с пользователем)

Пользователь уже прислал 3-й пример (read-back/query ответ после сохранения тренировки с `sets=3`), который снял часть неизвестных:

- **Подтверждено:** повтор (`sets`) не разворачивается в `exercises[]` — при `sets=1` и `sets=3` список экзерсайзов одинаковый (5 штук: warmup, group, work, rest, cooldown). Повтор целиком описывается полем `sets` на group-узле (`isGroup:true`). Rest-фаза внутри интервала — отдельный exercise `exerciseType=4` с `groupId`, указывающим на group; финальный cooldown — `exerciseType=3` с `groupId=""`. Итоговый `totalSets`/`sets` на программе = `1 (warmup) + 2×reps (work+rest) + 1 (cooldown)` (проверено: 4 при reps=1, 8 при reps=3) — это считает сам Coros, руками не пересчитываем.
- **Подтверждено:** `exerciseBarChart` (и в `programs[]`, и в `entities[]`) — чисто производная от `exercises[]`/`sets` структура, которую возвращает сам бэкенд — просто прокидываем как есть из ответа `/calculate`/query, не генерируем сами.
- **Подтверждено (с осторожностью):** `idInPlan`/`versionObjects[].id` = `"79"` в обоих независимых примерах (reps=1 и reps=3, разные тестовые сохранения) — похоже на стабильную константу для одиночных (вне многонедельного плана) тренировок, а не на что-то, что нужно вычислять запросом расписания.

**4-й пример (разные типы интенсивности/таргетов, август 2026) дополнительно подтвердил:**

- **Pace**: `intensityType=3`, значение = сек/км × 1000 (259000 = 4:19/км), `intensityMultiplier: 1000`, `intensityDisplayUnit: "1"` (строка), `hrType: 0`.
- **Кастомный HR-диапазон**: `intensityType=2`, `hrType=2`, `isIntensityPercent: false`, значения в bpm (HR-зона из шаблона — `hrType=3` + `intensityPercent`).
- **Power** = `intensityType=6` (ватты), **Cadence** = `intensityType=7` (spm).
- **Distance-таргет**: `targetType=5`, значение в сантиметрах (100000 = 1 км), `targetDisplayUnit: 1`; **Open** = `targetType=1`.
- `entities[].exerciseBarChart` == `programs[].exerciseBarChart` (проксирование из `/calculate` подтверждено).
- ❗ **`idInPlan` НЕ константа**: в 4-м примере — `80` (был `79`). Это инкрементирующийся per-account счётчик; веб-клиент берёт его из запроса загрузки календаря (эндпоинт пока не перехвачен).

**5-й пример (`GET /training/schedule/query?startDate=...&endDate=...&supportRestExercise=1`) закрыл вопрос idInPlan:**

- Ответ содержит на корне `data` готовое поле `maxIdInPlan` (и `maxPlanProgramId`) — следующий id = `maxIdInPlan + 1`. Реализовано в `CorosWorkoutService._resolve_id_in_plan` (env `WORKOUT_PLANNER_ID_IN_PLAN` остался как debug-override).
- Конверт ответа Coros — `{"result": "0000", "message": "OK", "data": {...}}` — подтверждён.
- Group-узел в сохранённой тренировке: `targetType/targetValue` = сумма таргетов детей за повтор — подтверждено повторно (600 = 300+300), досчитывает сервер.

Осталось закрыть (не блокирует live-тест):

1. **Тело ответа `/training/program/calculate`** — валидировать при первом dry-run, что ответ содержит все нужные для `/schedule/update` поля программы (design-решение "проксируем ответ calculate напрямую в programs[]").
2. **Подтвердить гипотезу про два вида отдыха** — recovery внутри повтора (`exerciseType=4`) vs пауза между сетами (`restValue` group-узла): проверится на первом live-тесте.

## Data model

### Внутренняя схема (LLM → это; независима от Coros wire-формата)

`workout_planner/models/plan.py` (обычные `pydantic.BaseModel`, не `CamelModel` — это внутреннее представление, не API-shape):

```python
class IntensityTarget(BaseModel):
    type: Literal["hr", "pace", "none"]
    value: float | None = None       # bpm или сек/км
    value_extend: float | None = None  # верхняя граница зоны, опционально

class DurationTarget(BaseModel):
    type: Literal["time", "distance"]
    value: float                      # секунды либо метры

class SimpleStep(BaseModel):
    kind: Literal["warmup", "cooldown"]
    duration: DurationTarget
    intensity: IntensityTarget | None = None

class IntervalStep(BaseModel):
    kind: Literal["interval"] = "interval"
    sets: int
    work_duration: DurationTarget
    work_intensity: IntensityTarget
    rest_duration: DurationTarget            # восстановление внутри каждого повтора (exerciseType=4)
    rest_intensity: IntensityTarget | None = None
    rest_between_sets_sec: int = 0           # пауза между сетами (restValue на group-узле); 0 = без паузы

class WorkoutPlan(BaseModel):
    sport_type: Literal["running"] = "running"   # v1: только running
    name: str
    target_date: date                             # уже резолвнутая LLM'ом дата
    steps: list[SimpleStep | IntervalStep]
```

Это именно то, что просил пользователь: `sets > 1` и `pace` заложены в схему с самого начала (`IntensityTarget.type == "pace"`, `IntervalStep.sets`). `steps` объявить как discriminated union по полю `kind` (`Field(discriminator="kind")`) — надёжнее валидация и чище JSON-схема для LLM.

### Wire-формат Coros (`workout_planner/models/coros_wire.py`, `CamelModel`-based)

Мэппинг на основе присланных payload'ов (подтверждено на примерах с `sets=1` и `sets=3` — структура `exercises[]` не меняется от количества повторов):
- `SimpleStep(kind="warmup")` → один exercise `exerciseType=1` (`sid_run_warm_up_dist`/`_time` — overview зависит от duration.type).
- `SimpleStep(kind="cooldown")` → один exercise `exerciseType=3`, `groupId=""`.
- `IntervalStep` → **три** exercise, независимо от `sets`: group-контейнер (`isGroup=true`, `exerciseType=0`, `sets=N` — это и есть repeat-count) + child `exerciseType=2` (work, `groupId`=id контейнера, `targetType/targetValue` из `work_duration`, `intensityType/intensityValue(+Extend)` из `work_intensity`) + child `exerciseType=4` (recovery-шаг внутри каждого повтора, тот же `groupId`, `targetType/targetValue` из `rest_duration`; переиспользует шаблонные name/overview от cooldown — вероятно потому что "лёгкий бег/rest" физиологически то же самое, что cooldown-шаблон в библиотеке Coros).
- **Два разных вида отдыха — не путать:** child `exerciseType=4` = восстановление внутри каждого повтора (наш `rest_duration`); `restValue` на group-узле = пауза между сетами (наш `rest_between_sets_sec`, в обоих примерах `30`). Мапить пользовательский rest в оба места сразу — ошибка (отдых задублируется).
- `id`/`groupId` — последовательно нумеруются при сборке (1, 2, 3, ...) как локальные ссылочные id внутри запроса; финальные (снежинко-подобные) id программе/exercise/entity присваивает сервер при сохранении — наши локальные id используются только для связи `groupId`, реальные не нужны в create-запросе.
- Group-узел: его собственные `targetType`/`targetValue` = сумма таргетов детей за один повтор (в read-back примере с sets=3: `600` = 300 work + 300 rest, `targetType: 2`). В draft-запросе `/calculate` веб-клиент оставлял их пустыми (`""`/`0`) — значит, их досчитывает сервер; в нашем draft тоже оставляем пустыми и берём из ответа `/calculate`.
- `exerciseBarChart` — НЕ генерируем сами: значение из ответа `/calculate` (или что вернёт read-back) копируется в `programs[].exerciseBarChart` и `entities[].exerciseBarChart` как есть.
- Все "boilerplate"-поля без явной семантики для бега (`equipment: [1]`, `part: [0]`, `sourceId: "0"`, `sourceUrl: ""`, `access: 0`, `hrType: 3`, `poolLength`/`poolLengthId`/`poolLengthUnit` дефолты, `subType: 0`, `isDefaultAdd` и т.п.) — берём константами из присланного примера как шаблон per `exerciseType`; если после доразведки pace-примера (пункт 1 выше) окажется, что часть из них влияет на pace-таргеты — скорректируем.

### Flow вызовов к Coros

```
draft_program = build_draft_program(plan)          # targetType/Value заполнены, duration/distance/trainingLoad = 0
calculated = POST /training/program/calculate  ->  response body (весь обогащённый program-объект)
# используем calculated НАПРЯМУЮ как programs[0], а не пытаемся руками копировать
# отдельные поля — так мы не зависим от точного списка того, что бэкенд досчитывает
schedule_payload = {
    "entities": [{"happenDay": plan.target_date.strftime("%Y%m%d"), "idInPlan": <id>, "sortNo": 0, "dayNo": 0,
                  "sortNoInPlan": 0, "sortNoInSchedule": 0, "exerciseBarChart": <derived from calculated.exercises>}],
    "programs": [{**calculated, "idInPlan": <id>}],
    "versionObjects": [{"id": <id>, "status": 1}],
    "pbVersion": 2,
}
POST /training/schedule/update
```

`<id>` — судя по двум независимым примерам пользователя (`sets=1` и `sets=3`), это стабильная константа `79` для одиночных тренировок. Закладываем как именованную константу в `workout_planner/constants.py` (с комментарием откуда она и что при `KeyError`/400 от Coros имеет смысл перепроверить через доразведку, а не как "магическое число без объяснений"), а не как отдельный resolve-запрос — до первого live-теста подтвердим доразведкой (п.2 выше), что она не меняется от содержимого/даты.

## Module layout

```
workout_planner/
├── __init__.py
├── configuration.py        # OpenRouterConfiguration(BaseSettings, env_prefix="openrouter_") — module-level singleton, как RedisConfiguration
├── constants.py            # свои API_URLS (calculate/schedule_update), enum'ы ExerciseType/TargetType/IntensityType
├── models/
│   ├── __init__.py
│   ├── plan.py             # WorkoutPlan, SimpleStep, IntervalStep, DurationTarget, IntensityTarget (внутренняя схема)
│   └── coros_wire.py        # CorosExercise, CorosProgram, CorosScheduleEntity, CorosScheduleUpdateRequest (CamelModel)
├── services/
│   ├── __init__.py
│   ├── llm_service.py       # OpenRouterService: text (+ today's date) -> WorkoutPlan, через JSON schema
│   ├── mapper.py            # WorkoutPlan -> draft CorosProgram/exercises
│   └── coros_workout_service.py  # CorosWorkoutService(BaseService): calculate() + schedule_update()
```

Никаких новых pip-зависимостей — `requests` и `pydantic` уже в `Pipfile`.

## Telegram integration

- `telegram/states/workout_planner.py` — новый `StatesGroup` (по аналогии с `telegram/states/registration.py`): `awaiting_description`, `awaiting_confirmation`.
- `telegram/handlers/workout_planner/` — новый subpackage со своим `Router()` (`workout_planner_router`), по аналогии с `telegram/handlers/sport/`:
  - Хендлер на команду (например `/plan_workout`, добавить в `BOT_COMMANDS` в `telegram/app.py`) → просит описание текстом.
  - Хендлер на текстовое сообщение в состоянии `awaiting_description` → `asyncio.to_thread(OpenRouterService(...).parse, text, today=date.today())` → `WorkoutPlan` → рендерит человекочитаемый предпросмотр (шаги + дата) + inline-клавиатуру confirm/cancel (новые константы в `telegram/keyboards.py`, конвенция `"workout:confirm"`/`"workout:cancel"`) → сохраняет `plan.model_dump_json()` в `state.update_data(...)`, стейт → `awaiting_confirmation`.
  - Callback-хендлер `confirm` → достаёт план из `state.get_data()`, `user_ctx.coros_config`, `asyncio.to_thread(AuthService(coros_config).get_or_set_access_token)`, затем `asyncio.to_thread(CorosWorkoutService(coros_config).create_and_schedule, plan)` → сообщение об успехе/ошибке (тот же try/except + `logger.error(..., exc_info=True)` паттерн, что в `latest_activity_handlers.py`) → `state.clear()`.
  - Callback `cancel` → `state.clear()` + подтверждение отмены.
  - Применить `UserContextMiddleware()` на `workout_planner_router` так же, как это делает `telegram/handlers/sport/__init__.py` для `main_router` (нужен `user_ctx` для `coros_config`).
- Зарегистрировать роутер: экспорт из `telegram/handlers/__init__.py` + `dispatcher.include_router(handlers.workout_planner_router)` в `telegram/app.py`.

## Implementation steps

1. **Доразведка** (см. раздел выше, п.1–3) — совместно с пользователем, до начала кода mapper/service.
2. `workout_planner/configuration.py` — `OpenRouterConfiguration` (`api_key`, `model` с дефолтом на дешёвую/быструю модель, `base_url` дефолт `https://openrouter.ai/api/v1`), добавить переменные в `example.env`.
3. `workout_planner/models/plan.py` — внутренняя схема.
4. `workout_planner/services/llm_service.py` — промпт с системным сообщением (описание доступных полей/enum'ов, today's date для резолва относительных дат типа "завтра"), `response_format` с JSON-схемой от `WorkoutPlan.model_json_schema()`, парсинг + `model_validate_json`, retry на невалидный JSON (1 повтор).
5. `workout_planner/constants.py` + `models/coros_wire.py` + `services/mapper.py` — сборка draft program/exercises по правилам из раздела Data model.
6. `workout_planner/services/coros_workout_service.py` — `calculate()` и `create_and_schedule(plan)` (id-константа `SINGLE_WORKOUT_PLAN_ID = 79` из `constants.py`, без отдельного resolve-запроса), плюс **dry-run флаг** (просто логирует/возвращает финальный payload без реального POST) — полезно для первых ручных тестов схемы без риска намусорить в расписании. Всем HTTP-вызовам (Coros и OpenRouter) задать явные timeout'ы — зависший вызов внутри `asyncio.to_thread` навсегда занимает поток и молча вешает хендлер.
7. `telegram/states/workout_planner.py`, `telegram/handlers/workout_planner/`, правки в `telegram/keyboards.py`, `telegram/handlers/__init__.py`, `telegram/app.py`.
8. Ручной end-to-end тест (см. Verification).

## Verification

- Юнит-уровень: собрать `WorkoutPlan` вручную (без LLM) для случая из присланного примера (warmup+work+cooldown, HR-таргет, sets=1) и для интервального (sets=4, pace) → прогнать через `mapper` → сравнить сгенерированный JSON с реальными присланными payload'ами (структурное совпадение полей).
- Dry-run: включить dry-run флаг, прогнать реальный текстовый запрос через LLM → мэппер → залогировать финальный `/schedule/update` payload, визуально сверить с рабочим примером.
- Live-тест: выключить dry-run, создать тестовую тренировку через бота на сегодня/завтра → проверить, что она появилась в Coros app (Training → Calendar) на нужной дате с правильными шагами → синхронизировать часы через приложение → убедиться, что тренировка появилась на часах.
- Проверить, что существующий Coros→Garmin sync (`/sync latest`, autosync) не задет — новый модуль не должен ничего импортировать в обратную сторону (`coros/` не должен знать о `workout_planner/`).
- Прогнать `black` и `mypy` по новому коду (конвенции репо, mypy проверяется в CI).

## Known risks

- Недокументированный write-эндпоинт может измениться в любой момент без предупреждения (как уже было с доменом API в этом проекте — см. память `coros-api-domain-typo`) — изоляция в отдельном модуле именно для этого.
- `idInPlan`/`versionObjects` — похоже на стабильную константу (`79` в обоих примерах пользователя), но подтверждено только на 2 наблюдениях от одного аккаунта; если в проверке (доразведка п.2) окажется, что она меняется (например, зависит от аккаунта или растёт со временем), придётся добавить резолвинг через query-эндпоинт расписания перед `schedule_update`.
- Отсутствие подтверждённого response body `/calculate` — решение "проксировать ответ напрямую" снижает риск, но нужно валидировать, что ответ действительно содержит все нужные для `/schedule/update` поля программы.
