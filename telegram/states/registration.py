from aiogram.fsm.state import State, StatesGroup

__all__ = ["RegistrationStates", "GarminRelinkStates"]


class RegistrationStates(StatesGroup):
    coros_email = State()
    coros_password = State()
    garmin_email = State()
    garmin_password = State()


class GarminRelinkStates(StatesGroup):
    garmin_email = State()
    garmin_password = State()
