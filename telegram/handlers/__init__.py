from telegram.handlers.base import router as base_router
from telegram.handlers.registration import registration_router
from telegram.handlers.sport import main_router as sport_router
from telegram.handlers.stats import stats_router
from telegram.handlers.workout_planner import workout_planner_router

__all__ = [
    "base_router",
    "registration_router",
    "sport_router",
    "stats_router",
    "workout_planner_router",
]
