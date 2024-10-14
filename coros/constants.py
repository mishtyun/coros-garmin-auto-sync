from enum import Enum

__all__ = ["ActivityFileType"]


class ActivityFileType(Enum):
    FIT = 4
    TCX = 3
    CSV = 0
