import json
import logging
from datetime import date, timedelta

from coros.services import AuthService, BaseService

from workout_planner.configuration import (
    WorkoutPlannerConfiguration,
    workout_planner_configuration,
)
from workout_planner.constants import API_URLS, PB_VERSION
from workout_planner.models import WorkoutPlan
from workout_planner.services.mapper import build_draft_program

logger = logging.getLogger(__name__)

__all__ = ["CorosWorkoutService", "CorosWorkoutError"]


class CorosWorkoutError(Exception):
    pass


TOKEN_INVALID_RESULT = "1019"


class CorosWorkoutService(BaseService):
    def __init__(self, configuration, planner_configuration=None):
        super().__init__(configuration)
        self.planner_configuration: WorkoutPlannerConfiguration = (
            planner_configuration or workout_planner_configuration
        )

    def get_url(self, url_key: str, **query_params) -> str:
        return self.configuration.api_url + API_URLS[url_key].format(**query_params)

    def get_headers(self) -> dict:
        headers = super().get_headers()
        headers.update(
            {
                "accesstoken": self.redis_repository.get_access_token(
                    self.configuration.email
                ),
            }
        )
        return headers

    def _refresh_access_token(self) -> None:
        access_token = AuthService(self.configuration).send_login_request(
            return_token=True
        )
        if not access_token:
            raise CorosWorkoutError("Coros re-login failed")
        self.redis_repository.add_access_token(self.configuration.email, access_token)

    def _request(
        self, method: str, url: str, payload: dict | None = None, retry: bool = True
    ) -> dict:
        kwargs: dict = {
            "headers": self.get_headers(),
            "timeout": self.planner_configuration.request_timeout,
        }
        if payload is not None:
            kwargs["json"] = payload

        response = self.http.request(method, url, **kwargs)
        if response.status != 200:
            raise CorosWorkoutError(
                f"Coros returned HTTP {response.status} for {url}: {response.reason}"
            )

        body = response.json()
        # Coros wraps errors in {"result": "...", "message": "..."};
        # "0000" is the success code across their API.
        result_code = body.get("result")
        if result_code == TOKEN_INVALID_RESULT and retry:
            # The cached token can be invalidated server-side before our
            # 30-min Redis TTL expires (e.g. logging into Training Hub web
            # issues a new token) — re-login once and retry.
            logger.info("Coros access token invalid, re-authenticating")
            self._refresh_access_token()
            return self._request(method, url, payload, retry=False)
        if result_code is not None and result_code != "0000":
            raise CorosWorkoutError(
                f"Coros request to {url} failed: result={result_code}, "
                f"message={body.get('message')}"
            )
        return body

    def _post(self, url_key: str, payload: dict) -> dict:
        return self._request("POST", self.get_url(url_key), payload)

    def calculate(self, draft_program: dict) -> dict:
        # Returns computed stats for the draft (planDuration, planDistance,
        # planTrainingLoad, planSets, exerciseBarChart, ...) — NOT a program
        # object; the web client merges these into the draft itself.
        body = self._post("calculate", draft_program)
        calculated = body.get("data") or {}
        if not calculated.get("exerciseBarChart"):
            raise CorosWorkoutError(
                "Unexpected /training/program/calculate response shape: "
                f"{json.dumps(body)[:500]}"
            )
        return calculated

    def _query_schedule(self, start_date: date, end_date: date) -> dict:
        return self._request(
            "GET",
            self.get_url(
                "schedule_query",
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
            ),
        )

    def _resolve_id_in_plan(self) -> int:
        # Optional manual override, mostly for debugging.
        if self.planner_configuration.id_in_plan is not None:
            return self.planner_configuration.id_in_plan

        # idInPlan is an incrementing per-account counter (observed 79 -> 80);
        # the schedule query returns the current maximum as data.maxIdInPlan.
        today = date.today()
        body = self._query_schedule(
            today - timedelta(days=7), today + timedelta(days=7)
        )
        max_id_in_plan = body.get("data", {}).get("maxIdInPlan")
        if max_id_in_plan is None:
            raise CorosWorkoutError(
                "schedule_query response has no data.maxIdInPlan: "
                f"{json.dumps(body)[:500]}"
            )
        return int(max_id_in_plan) + 1

    @staticmethod
    def build_schedule_payload(
        plan: WorkoutPlan, draft_program: dict, calculated: dict, id_in_plan: int
    ) -> dict:
        exercise_bar_chart = calculated.get("exerciseBarChart", [])
        # Merge the draft with the computed stats, mirroring what the
        # Training Hub web client sends to /training/schedule/update.
        program = {
            **draft_program,
            "idInPlan": id_in_plan,
            "distance": calculated.get("planDistance", 0),
            "duration": calculated.get("planDuration", 0),
            "trainingLoad": calculated.get("planTrainingLoad", 0),
            "totalSets": calculated.get("planSets", 0),
            "sets": calculated.get("planSets", 0),
            "pitch": calculated.get("planPitch", 0),
            "distanceDisplayUnit": calculated.get("distanceDisplayUnit", 1),
            "exerciseBarChart": exercise_bar_chart,
        }

        return {
            "entities": [
                {
                    "happenDay": plan.target_date.strftime("%Y%m%d"),
                    "idInPlan": id_in_plan,
                    "sortNo": 0,
                    "dayNo": 0,
                    "sortNoInPlan": 0,
                    "sortNoInSchedule": 0,
                    "exerciseBarChart": exercise_bar_chart,
                }
            ],
            "programs": [program],
            "versionObjects": [{"id": id_in_plan, "status": 1}],
            "pbVersion": PB_VERSION,
        }

    def create_and_schedule(self, plan: WorkoutPlan) -> dict:
        draft_program = build_draft_program(plan)
        calculated = self.calculate(draft_program)
        id_in_plan = self._resolve_id_in_plan()
        payload = self.build_schedule_payload(
            plan, draft_program, calculated, id_in_plan
        )

        if self.planner_configuration.dry_run:
            logger.info(
                f"[dry-run] /training/schedule/update payload:\n"
                f"{json.dumps(payload, indent=2)}"
            )
            return {"dry_run": True, "payload": payload}

        body = self._post("schedule_update", payload)
        logger.info(
            f"Scheduled workout '{plan.name}' on {plan.target_date} "
            f"(idInPlan={id_in_plan})"
        )
        return body
