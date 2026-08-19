import asyncio
import json
import logging
from datetime import date

from aiogram import F, Router, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile

from coros.services import AuthService
from telegram.keyboards import (
    WorkoutPlannerCallbacks,
    get_workout_confirm_inline_keyboard,
)
from telegram.states.workout_planner import WorkoutPlannerStates
from users.context import UserContext
from workout_planner.models import IntervalStep, SimpleStep, WorkoutPlan
from workout_planner.services import CorosWorkoutService, OpenRouterService
from workout_planner.services.llm_service import WorkoutParseError

logger = logging.getLogger(__name__)

__all__ = ["workout_planner_router"]

workout_planner_router = Router()

PLAN_STATE_KEY = "workout_plan_json"


def _format_duration(duration) -> str:
    if duration.type == "distance":
        if duration.value >= 1000:
            return f"{duration.value / 1000:g} km"
        return f"{duration.value:g} m"
    minutes, seconds = divmod(int(duration.value), 60)
    return f"{minutes}:{seconds:02d} min" if seconds else f"{minutes} min"


def _format_intensity(intensity) -> str:
    if intensity is None or intensity.type == "none" or intensity.value is None:
        return ""
    value = intensity.value
    extend = intensity.value_extend
    if intensity.type == "hr":
        rng = f"{value:g}-{extend:g}" if extend and extend != value else f"{value:g}"
        return f" @ {rng} bpm"

    # pace, sec/km
    def fmt(v):
        m, s = divmod(int(v), 60)
        return f"{m}:{s:02d}"

    rng = f"{fmt(value)}-{fmt(extend)}" if extend and extend != value else fmt(value)
    return f" @ {rng}/km"


def render_plan_preview(plan: WorkoutPlan) -> str:
    lines = [f"🏃 <b>{plan.name}</b>", f"📅 {plan.target_date.isoformat()}", ""]
    for step in plan.steps:
        if isinstance(step, SimpleStep):
            icon = "🔥" if step.kind == "warmup" else "🧊"
            lines.append(
                f"{icon} {step.kind.capitalize()}: "
                f"{_format_duration(step.duration)}{_format_intensity(step.intensity)}"
            )
        elif isinstance(step, IntervalStep):
            lines.append(
                f"🔁 {step.sets}x {_format_duration(step.work_duration)}"
                f"{_format_intensity(step.work_intensity)}, "
                f"rest {_format_duration(step.rest_duration)}"
                f"{_format_intensity(step.rest_intensity)}"
            )
            if step.rest_between_sets_sec:
                lines.append(f"   ⏸ {step.rest_between_sets_sec}s between sets")
    lines.append("")
    lines.append("Schedule this workout in Coros?")
    return "\n".join(lines)


@workout_planner_router.message(Command("plan_workout"))
async def plan_workout_command_handler(message: types.Message, state: FSMContext):
    await state.set_state(WorkoutPlannerStates.awaiting_description)
    await message.answer(
        "Describe the workout in free text, e.g.:\n"
        "<i>10 min warm-up, 4x400m at 4:30/km with 2 min rest, "
        "10 min cool-down, tomorrow</i>",
        parse_mode="HTML",
    )


@workout_planner_router.message(
    StateFilter(WorkoutPlannerStates.awaiting_description), F.text
)
async def workout_description_handler(message: types.Message, state: FSMContext):
    if not message.text:
        return

    await message.answer("Parsing your workout... 🤖")
    try:
        plan = await asyncio.to_thread(
            OpenRouterService().parse, message.text, date.today()
        )
    except WorkoutParseError as e:
        logger.error(f"Error while parsing workout description: {str(e)}")
        await message.answer(
            "Could not understand the workout description, try rephrasing it"
        )
        return
    except Exception as e:
        logger.error(
            f"Error while parsing workout description: {str(e)}", exc_info=True
        )
        await message.answer("Error while parsing the description")
        return

    await state.update_data({PLAN_STATE_KEY: plan.model_dump_json()})
    await state.set_state(WorkoutPlannerStates.awaiting_confirmation)
    await message.answer(
        render_plan_preview(plan),
        parse_mode="HTML",
        reply_markup=get_workout_confirm_inline_keyboard(),
    )


@workout_planner_router.callback_query(
    StateFilter(WorkoutPlannerStates.awaiting_confirmation),
    F.data == WorkoutPlannerCallbacks.CONFIRM,
)
async def workout_confirm_handler(
    callback_query: types.CallbackQuery, state: FSMContext, user_ctx: UserContext
):
    await callback_query.answer()
    data = await state.get_data()
    plan_json = data.get(PLAN_STATE_KEY)
    if not plan_json:
        await state.clear()
        await callback_query.message.answer(
            "Workout draft expired, start over with /plan_workout"
        )
        return

    plan = WorkoutPlan.model_validate_json(plan_json)
    try:
        coros_config = user_ctx.coros_config
        await asyncio.to_thread(AuthService(coros_config).get_or_set_access_token)
        result = await asyncio.to_thread(
            CorosWorkoutService(coros_config).create_and_schedule, plan
        )

        if result.get("dry_run"):
            payload_file = BufferedInputFile(
                filename="schedule_update_payload.json",
                file=json.dumps(result["payload"], indent=2).encode(),
            )
            await callback_query.message.answer_document(
                document=payload_file,
                caption="Dry run — payload that would be sent to Coros",
            )
        else:
            await callback_query.message.answer(
                f"Scheduled! ✅\n'{plan.name}' on {plan.target_date.isoformat()} — "
                "sync your watch via the Coros app to get it on the wrist"
            )
    except Exception as e:
        logger.error(f"Error while scheduling workout: {str(e)}", exc_info=True)
        await callback_query.message.answer("Error while scheduling the workout")
    finally:
        await state.clear()


@workout_planner_router.callback_query(F.data == WorkoutPlannerCallbacks.CANCEL)
async def workout_cancel_handler(
    callback_query: types.CallbackQuery, state: FSMContext
):
    await callback_query.answer()
    await state.clear()
    await callback_query.message.answer("Workout planning cancelled")
