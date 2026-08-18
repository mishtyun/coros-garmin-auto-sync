from telegram.handlers.sport.base_handlers import router as main_router
from telegram.handlers.sport.calendar_handlers import calendar_router
from telegram.handlers.sport.daily_get_handlers import daily_router as daily_router__get
from telegram.handlers.sport.latest_activity_handlers import latests_router
from telegram.handlers.sport.daily_sync_handlers import (
    daily_router as daily_router__sync,
)
from telegram.middlewares import UserContextMiddleware

main_router.include_routers(
    latests_router, daily_router__get, daily_router__sync, calendar_router
)

user_context_middleware = UserContextMiddleware()
main_router.message.middleware(user_context_middleware)
main_router.callback_query.middleware(user_context_middleware)


__all__ = ["main_router"]
