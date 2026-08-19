from telegram.handlers.workout_planner.handlers import workout_planner_router
from telegram.middlewares import UserContextMiddleware

user_context_middleware = UserContextMiddleware()
workout_planner_router.message.middleware(user_context_middleware)
workout_planner_router.callback_query.middleware(user_context_middleware)

__all__ = ["workout_planner_router"]
