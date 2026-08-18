from telegram.handlers.base import router as base_router
from telegram.handlers.registration import registration_router
from telegram.handlers.sport import main_router as sport_router

__all__ = ["base_router", "registration_router", "sport_router"]
