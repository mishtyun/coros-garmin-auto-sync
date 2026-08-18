from pydantic import BaseModel

__all__ = ["UserProfile"]


class UserProfile(BaseModel):
    tg_id: int
    coros_email: str
    coros_password_md5: str
    garmin_email: str
    created_at: str
    autosync: bool = False
    autosync_quiet: bool = False
