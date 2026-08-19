from core.schemas import CamelModel

__all__ = ["ActivityShortSchema"]


class ActivityShortSchema(CamelModel):
    date: int
    label_id: str
    name: str | None = None
    sport_type: int

    # optional list-endpoint metrics (present in Coros /activity/query responses)
    distance: float | None = None  # meters
    total_time: float | None = None  # elapsed seconds
    workout_time: float | None = None  # moving seconds

    @property
    def duration(self) -> float | None:
        return self.workout_time or self.total_time
