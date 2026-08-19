from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = [
    "OpenRouterConfiguration",
    "WorkoutPlannerConfiguration",
    "openrouter_configuration",
    "workout_planner_configuration",
]


class OpenRouterConfiguration(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="openrouter_", extra="ignore")

    api_key: str | None = None
    model: str = Field(default="openai/gpt-4o-mini")
    base_url: str = Field(default="https://openrouter.ai/api/v1")
    request_timeout: int = 60


class WorkoutPlannerConfiguration(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="workout_planner_", extra="ignore")

    # When enabled, the final /schedule/update payload is returned/logged
    # instead of being POSTed to Coros — for validating the wire format
    # against reverse-engineered examples without polluting the schedule.
    dry_run: bool = False
    request_timeout: int = 30
    # Manual override for idInPlan (debugging only) — normally it is resolved
    # automatically from the schedule query's data.maxIdInPlan + 1.
    id_in_plan: int | None = None


openrouter_configuration = OpenRouterConfiguration()
workout_planner_configuration = WorkoutPlannerConfiguration()
