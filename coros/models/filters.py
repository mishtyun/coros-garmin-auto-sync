from pydantic import BaseModel, Field

__all__ = ["DateActivityFilter"]


class DateActivityFilter(BaseModel):
    start_date: str = Field(examples=["20241003"])
    end_date: str = Field(examples=["20241003"])
