"""WorkoutPlan -> Coros draft program payload (input of /training/program/calculate).

Boilerplate field values come from captured Training Hub traffic — see
workout_planner/constants.py for provenance notes.
"""

import copy

from workout_planner.constants import (
    DISTANCE_TARGET_FACTOR,
    GROUP_EXERCISE_TEMPLATE,
    PACE_VALUE_FACTOR,
    PROGRAM_DRAFT_TEMPLATE,
    STEP_EXERCISE_TEMPLATES,
    ExerciseType,
    HrType,
    IntensityType,
    TargetType,
)
from workout_planner.models import (
    DurationTarget,
    IntensityTarget,
    IntervalStep,
    SimpleStep,
    WorkoutPlan,
)

__all__ = ["build_draft_program"]


def _apply_duration(exercise: dict, duration: DurationTarget) -> None:
    if duration.type == "time":
        exercise["targetType"] = TargetType.TIME.value
        exercise["targetValue"] = int(duration.value)
        exercise["targetDisplayUnit"] = 0
    else:  # distance
        exercise["targetType"] = TargetType.DISTANCE.value
        exercise["targetValue"] = int(duration.value * DISTANCE_TARGET_FACTOR)
        exercise["targetDisplayUnit"] = 1


def _apply_intensity(exercise: dict, intensity: IntensityTarget | None) -> None:
    if intensity is None or intensity.type == "none" or intensity.value is None:
        return

    value = intensity.value
    value_extend = (
        intensity.value_extend if intensity.value_extend is not None else value
    )

    if intensity.type == "hr":
        exercise["intensityType"] = IntensityType.HEART_RATE.value
        exercise["hrType"] = HrType.CUSTOM_RANGE.value
        exercise["intensityValue"] = int(value)
        exercise["intensityValueExtend"] = int(value_extend)
    else:  # pace, sec/km
        exercise["intensityType"] = IntensityType.PACE.value
        exercise["hrType"] = HrType.NONE.value
        exercise["intensityValue"] = int(value * PACE_VALUE_FACTOR)
        exercise["intensityValueExtend"] = int(value_extend * PACE_VALUE_FACTOR)
        exercise["intensityMultiplier"] = PACE_VALUE_FACTOR
        # the web client sends this display-unit flag as a string for pace
        exercise["intensityDisplayUnit"] = "1"

    exercise["isIntensityPercent"] = False
    exercise["intensityCustom"] = 0


def _build_step_exercise(
    exercise_type: ExerciseType,
    duration: DurationTarget,
    intensity: IntensityTarget | None,
    exercise_id: int,
    sort_no: int,
    group_id: int | str = "",
) -> dict:
    exercise = copy.deepcopy(STEP_EXERCISE_TEMPLATES[exercise_type])
    exercise["id"] = exercise_id
    exercise["sortNo"] = sort_no
    exercise["groupId"] = group_id
    _apply_duration(exercise, duration)
    _apply_intensity(exercise, intensity)
    return exercise


def _build_simple_step(step: SimpleStep, exercise_id: int, sort_no: int) -> list[dict]:
    exercise_type = (
        ExerciseType.WARMUP if step.kind == "warmup" else ExerciseType.COOLDOWN
    )
    return [
        _build_step_exercise(
            exercise_type, step.duration, step.intensity, exercise_id, sort_no
        )
    ]


def _build_interval_step(step: IntervalStep, group_id: int, sort_no: int) -> list[dict]:
    group = copy.deepcopy(GROUP_EXERCISE_TEMPLATE)
    group["id"] = group_id
    group["sortNo"] = sort_no
    group["sets"] = step.sets
    group["restValue"] = step.rest_between_sets_sec

    work = _build_step_exercise(
        ExerciseType.WORK,
        step.work_duration,
        step.work_intensity,
        exercise_id=group_id + 1,
        sort_no=sort_no,
        group_id=group_id,
    )
    rest = _build_step_exercise(
        ExerciseType.REST,
        step.rest_duration,
        step.rest_intensity,
        exercise_id=group_id + 2,
        sort_no=sort_no + 1,
        group_id=group_id,
    )
    return [group, work, rest]


def build_draft_program(plan: WorkoutPlan) -> dict:
    exercises: list[dict] = []
    next_id = 1
    sort_no = 1

    for step in plan.steps:
        if isinstance(step, SimpleStep):
            built = _build_simple_step(step, exercise_id=next_id, sort_no=sort_no)
        else:
            built = _build_interval_step(step, group_id=next_id, sort_no=sort_no)

        exercises.extend(built)
        next_id += len(built)
        sort_no += len(built)

    program = copy.deepcopy(PROGRAM_DRAFT_TEMPLATE)
    program["name"] = plan.name
    program["exercises"] = exercises
    return program
