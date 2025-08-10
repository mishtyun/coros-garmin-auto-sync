from aiogram.fsm.state import State, StatesGroup

__all__ = ["CalendarDatePicker"]


class CalendarDatePicker(StatesGroup):
    choosing_date = State()
