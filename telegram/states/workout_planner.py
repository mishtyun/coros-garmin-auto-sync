from aiogram.fsm.state import State, StatesGroup

__all__ = ["WorkoutPlannerStates"]


class WorkoutPlannerStates(StatesGroup):
    awaiting_description = State()
    awaiting_confirmation = State()
