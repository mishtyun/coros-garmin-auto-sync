"""Internal workout representation produced by the LLM.

Deliberately independent from the Coros wire format — the mapper in
services/mapper.py converts this into the reverse-engineered payloads.
"""

from datetime import date
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, model_validator

__all__ = [
    "IntensityTarget",
    "DurationTarget",
    "SimpleStep",
    "IntervalStep",
    "WorkoutPlan",
    "WorkoutStep",
]


class IntensityTarget(BaseModel):
    type: Literal["hr", "pace", "none"] = "none"
    # hr: bpm; pace: seconds per km (e.g. 5:30/km -> 330)
    value: float | None = None
    # upper bound of the range; if omitted, `value` is used for both bounds
    value_extend: float | None = None


class DurationTarget(BaseModel):
    # time: seconds; distance: meters; open: no target, ended by lap button
    type: Literal["time", "distance", "open"]
    value: float | None = None

    @model_validator(mode="after")
    def _validate_value(self) -> "DurationTarget":
        if self.type == "open":
            self.value = None
        elif self.value is None or self.value <= 0:
            raise ValueError(f"value must be > 0 for type '{self.type}'")
        return self


class SimpleStep(BaseModel):
    kind: Literal["warmup", "cooldown"]
    duration: DurationTarget
    intensity: IntensityTarget | None = None


class IntervalStep(BaseModel):
    kind: Literal["interval"] = "interval"
    sets: int = Field(ge=1)
    work_duration: DurationTarget
    work_intensity: IntensityTarget
    # recovery step inside each repetition
    rest_duration: DurationTarget
    rest_intensity: IntensityTarget | None = None
    # pause between sets (0 = none); distinct from rest_duration
    rest_between_sets_sec: int = Field(default=0, ge=0)


WorkoutStep = Annotated[Union[SimpleStep, IntervalStep], Field(discriminator="kind")]


class WorkoutPlan(BaseModel):
    sport_type: Literal["running"] = "running"
    name: str
    target_date: date
    steps: list[WorkoutStep] = Field(min_length=1)
