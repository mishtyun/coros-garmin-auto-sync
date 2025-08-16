from typing import NewType

from core.schemas import CamelModel

__all__ = ["GarminActivitySchema", "GarminActivitiesSchema"]


class GarminActivityTypeSchema(CamelModel):
    type_id: int
    type_key: str


class GarminActivityOwnerInfoSchema(CamelModel):
    owner_id: int
    owner_display_name: str
    owner_full_name: str
    owner_profile_image_url_small: str | None
    owner_profile_image_url_medium: str | None
    owner_profile_image_url_large: str | None


class GarminActivitySchema(GarminActivityOwnerInfoSchema):
    activity_id: int
    activity_name: str
    start_time_local: str
    start_time_gmt: str

    activity_type: GarminActivityTypeSchema

    distance: float
    duration: float

    location_name: str | None


GarminActivitiesSchema = NewType("GarminActivitiesSchema", list[GarminActivitySchema])
