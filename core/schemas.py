from pydantic import BaseModel, ConfigDict

__all__ = ["CamelModel"]


def to_camel(string: str) -> str:
    parts = string.split("_")
    alias = parts[0] + "".join(word.capitalize() for word in parts[1:])
    if "gmt" in string.lower():
        alias = alias.replace("Gmt", "GMT")
    return alias


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
