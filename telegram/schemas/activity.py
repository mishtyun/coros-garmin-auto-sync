from typing import NewType

from core.schemas import CamelModel

__all__ = ["GarminActivitySchema", "GarminActivitiesSchema"]


class GarminActivityTypeSchema(CamelModel):
    type_id: int
    type_key: str


class GarminActivityOwnerInfoSchema(CamelModel):
    owner_id: int | None = None
    owner_display_name: str | None = None
    owner_full_name: str | None = None
    owner_profile_image_url_small: str | None = None
    owner_profile_image_url_medium: str | None = None
    owner_profile_image_url_large: str | None = None


class GarminActivitySchema(GarminActivityOwnerInfoSchema):
    activity_id: int
    activity_name: str | None = None
    start_time_local: str | None = None
    start_time_gmt: str | None = None

    activity_type: GarminActivityTypeSchema

    distance: float | None = None
    duration: float | None = None

    location_name: str | None = None


GarminActivitiesSchema = NewType("GarminActivitiesSchema", list[GarminActivitySchema])
