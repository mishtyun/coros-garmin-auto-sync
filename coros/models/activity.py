from dataclasses import dataclass


@dataclass
class Activity:
    date: int
    labelId: str
    name: str
    sportType: int
