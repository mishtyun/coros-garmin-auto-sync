from core.schemas import CamelModel

__all__ = ["ActivityShortSchema"]


class ActivityShortSchema(CamelModel):
    date: int
    label_id: str
    name: str
    sport_type: int
