from pydantic import BaseModel, Field

__all__ = ["Activity"]


class Activity(BaseModel):
    date: int
    label_id: str = Field(validation_alias="labelId")
    name: str
    sport_type: int = Field(validation_alias="sportType")
