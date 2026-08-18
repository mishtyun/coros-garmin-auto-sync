from aiogram.fsm.state import State, StatesGroup

__all__ = ["RegistrationStates"]


class RegistrationStates(StatesGroup):
    coros_email = State()
    coros_password = State()
    garmin_email = State()
    garmin_password = State()
