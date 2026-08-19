import json
import logging
from datetime import date

import requests
from pydantic import ValidationError

from workout_planner.configuration import (
    OpenRouterConfiguration,
    openrouter_configuration,
)
from workout_planner.models import WorkoutPlan

logger = logging.getLogger(__name__)

__all__ = ["OpenRouterService", "WorkoutParseError"]


class WorkoutParseError(Exception):
    pass


SYSTEM_PROMPT_TEMPLATE = """\
You convert a free-text workout description into a structured JSON object.
Today's date is {today} — resolve relative dates like "tomorrow" against it.
If no date is mentioned, use today's date.

Respond with ONLY a JSON object matching this schema (no markdown, no prose):
{schema}

Rules:
- durations: type "time" -> value in seconds; type "distance" -> value in meters.
- intensity: type "hr" -> value/value_extend in bpm; type "pace" -> seconds per
  km (e.g. 5:30/km -> 330). Omit intensity or use type "none" when unspecified.
- "4x400m" style repeats -> one interval step with sets=4.
- rest_duration is the recovery inside each repetition; rest_between_sets_sec
  is an extra pause between sets (0 unless explicitly asked).
- name: short human-readable workout title in the language of the description.
- target_date: ISO format YYYY-MM-DD.
"""


class OpenRouterService:
    def __init__(self, configuration: OpenRouterConfiguration | None = None):
        self.configuration = configuration or openrouter_configuration
        if not self.configuration.api_key:
            raise WorkoutParseError("OpenRouter API key is not configured")

    @property
    def chat_url(self) -> str:
        return self.configuration.base_url + "/chat/completions"

    def _request_completion(self, messages: list[dict]) -> str:
        response = requests.post(
            self.chat_url,
            headers={"Authorization": f"Bearer {self.configuration.api_key}"},
            json={
                "model": self.configuration.model,
                "messages": messages,
                "response_format": {"type": "json_object"},
                "temperature": 0.1,
            },
            timeout=self.configuration.request_timeout,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def parse(self, description: str, today: date) -> WorkoutPlan:
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            today=today.isoformat(),
            schema=json.dumps(WorkoutPlan.model_json_schema()),
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": description},
        ]

        last_error: Exception | None = None
        for attempt in range(2):
            content = self._request_completion(messages)
            try:
                return WorkoutPlan.model_validate_json(content)
            except ValidationError as e:
                logger.warning(
                    f"LLM returned invalid workout JSON (attempt {attempt + 1}): {e}"
                )
                last_error = e
                messages.append({"role": "assistant", "content": content})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "The JSON does not match the schema, fix it. "
                            f"Validation errors: {e}"
                        ),
                    }
                )

        raise WorkoutParseError(f"Could not parse workout description: {last_error}")
