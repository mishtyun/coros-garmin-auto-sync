"""Constants for the reverse-engineered Coros Training Hub workout API.

All values below come from captured browser traffic of traininghub.coros.com
(DevTools, August 2026). The API is undocumented and may change without
notice — if Coros starts rejecting payloads, re-capture the requests and
update the templates/enums here.
"""

from enum import IntEnum

__all__ = [
    "API_URLS",
    "ExerciseType",
    "TargetType",
    "IntensityType",
    "HrType",
    "PACE_VALUE_FACTOR",
    "DISTANCE_TARGET_FACTOR",
    "PB_VERSION",
    "SPORT_TYPES",
    "GROUP_EXERCISE_TEMPLATE",
    "STEP_EXERCISE_TEMPLATES",
    "PROGRAM_DRAFT_TEMPLATE",
    "PROGRAM_SPORT_OVERRIDES",
]

API_URLS = {
    "calculate": "/training/program/calculate",
    "schedule_update": "/training/schedule/update",
    "schedule_query": (
        "/training/schedule/query"
        "?startDate={start_date}&endDate={end_date}&supportRestExercise=1"
    ),
}


class ExerciseType(IntEnum):
    GROUP = 0
    WARMUP = 1
    WORK = 2
    COOLDOWN = 3
    REST = 4  # recovery step inside an interval group


class TargetType(IntEnum):
    OPEN = 1  # no target, advance by lap button
    TIME = 2  # targetValue in seconds
    DISTANCE = 5  # targetValue in centimeters (1 km = 100000)


class IntensityType(IntEnum):
    NONE = 0
    HEART_RATE = 2  # intensityValue in bpm
    PACE = 3  # intensityValue in sec/km * 1000
    POWER = 6  # intensityValue in watts
    CADENCE = 7  # intensityValue in steps/min


class HrType(IntEnum):
    NONE = 0
    CUSTOM_RANGE = 2  # explicit bpm range, isIntensityPercent=false
    ZONE = 3  # zone-based, driven by intensityPercent fields


PACE_VALUE_FACTOR = 1000  # sec/km -> Coros pace units
DISTANCE_TARGET_FACTOR = 100  # meters -> Coros distance target units (cm)

PB_VERSION = 2

# The `sets` field of this node is the interval repeat count; `restValue`
# is the pause between sets in seconds (distinct from the in-set recovery
# step, which is a separate REST exercise inside the group).
GROUP_EXERCISE_TEMPLATE = {
    "access": 0,
    "defaultOrder": 0,
    "exerciseType": ExerciseType.GROUP.value,
    "id": 0,
    "intensityCustom": 0,
    "intensityMultiplier": 0,
    "intensityType": 0,
    "intensityValue": 0,
    "intensityValueExtend": 0,
    "isDefaultAdd": 0,
    "isGroup": True,
    "name": "",
    "originId": "",
    "overview": "",
    "programId": "",
    "restType": 0,
    "restValue": 0,
    "sets": 1,
    "sortNo": 0,
    "sourceId": "0",
    "sourceUrl": "",
    "sportType": 0,
    "subType": 0,
    "targetType": "",
    "targetValue": 0,
    "videoUrl": "",
}

_STEP_EXERCISE_BASE = {
    "access": 0,
    "equipment": [1],
    "groupId": "",
    "hrType": HrType.NONE.value,
    "id": 0,
    "intensityCustom": 0,
    "intensityDisplayUnit": 0,
    "intensityMultiplier": 0,
    "intensityPercent": 0,
    "intensityPercentExtend": 0,
    "intensityType": IntensityType.NONE.value,
    "intensityValue": 0,
    "intensityValueExtend": 0,
    "isDefaultAdd": 0,
    "isGroup": False,
    "isIntensityPercent": False,
    "part": [0],
    "restType": 3,
    "restValue": 0,
    "sets": 1,
    "sortNo": 0,
    "sourceId": "0",
    "sourceUrl": "",
    "sportType": 1,
    "subType": 0,
    "targetDisplayUnit": 0,
    "targetType": TargetType.TIME.value,
    "targetValue": 0,
    "userId": 0,
    "videoUrl": "",
}

SPORT_TYPES = {"running": 1, "cycling": 2}

# name/originId/overview identify built-in Coros exercise library entries
# (warm-up / training / cool-down per sport) that the web builder always uses.
_STEP_LIBRARY = {
    "running": {
        ExerciseType.WARMUP: {
            "createTimestamp": 1586584068,
            "defaultOrder": 1,
            "name": "T1120",
            "originId": "425895398452936705",
            "overview": "sid_run_warm_up_dist",
        },
        ExerciseType.WORK: {
            "createTimestamp": 1587381919,
            "defaultOrder": 2,
            "isDefaultAdd": 1,
            "name": "T3001",
            "originId": "426109589008859136",
            "overview": "sid_run_training",
        },
        ExerciseType.REST: {
            "createTimestamp": 1586584214,
            "defaultOrder": 3,
            "name": "T1123",
            "originId": "425895398452936705",
            "overview": "sid_run_cool_down_dist",
        },
        ExerciseType.COOLDOWN: {
            "createTimestamp": 1586584214,
            "defaultOrder": 3,
            "name": "T1122",
            "originId": "425895456971866112",
            "overview": "sid_run_cool_down_dist",
        },
    },
    "cycling": {
        ExerciseType.WARMUP: {
            "createTimestamp": 1586585721,
            "defaultOrder": 1,
            "name": "T1120",
            "originId": "425895398452936705",
            "overview": "sid_bike_warm_up_dist",
        },
        ExerciseType.WORK: {
            "createTimestamp": 1586585061,
            "defaultOrder": 2,
            "isDefaultAdd": 1,
            "name": "T4000",
            "originId": "426109589008859136",
            "overview": "sid_bike_dist_speed",
        },
        ExerciseType.REST: {
            "createTimestamp": 1586585838,
            "defaultOrder": 3,
            "name": "T1123",
            "originId": "425895398452936705",
            "overview": "sid_bike_cool_down_dist",
        },
        ExerciseType.COOLDOWN: {
            "createTimestamp": 1586585838,
            "defaultOrder": 3,
            "name": "T1122",
            "originId": "425895456971866112",
            "overview": "sid_bike_cool_down_dist",
        },
    },
}

STEP_EXERCISE_TEMPLATES = {
    sport: {
        exercise_type: {
            **_STEP_EXERCISE_BASE,
            "exerciseType": exercise_type.value,
            "sportType": SPORT_TYPES[sport],
            **library_entry,
        }
        for exercise_type, library_entry in library.items()
    }
    for sport, library in _STEP_LIBRARY.items()
}

PROGRAM_DRAFT_TEMPLATE = {
    "access": 1,
    "authorId": "0",
    "createTimestamp": 0,
    "distance": 0,
    "duration": 0,
    "essence": 0,
    "estimatedType": 0,
    "estimatedValue": 0,
    "exerciseNum": 0,
    "exercises": [],
    "headPic": "",
    "id": "0",
    "idInPlan": "0",
    "name": "",
    "nickname": "",
    "originEssence": 0,
    "overview": "",
    "pbVersion": PB_VERSION,
    "planIdIndex": 0,
    "poolLength": 2500,
    "profile": "",
    "referExercise": {"intensityType": 0, "hrType": 0, "valueType": 0},
    "sex": 0,
    "shareUrl": "",
    "simple": False,
    "sourceUrl": (
        "https://d31oxp44ddzkyk.cloudfront.net/source/source_default/0/"
        "ee2ec19837ba4093b7c8617eb2f9b1f5.jpg"
    ),
    "sportType": 1,
    "star": 0,
    "subType": 65535,
    "targetType": 0,
    "targetValue": 0,
    "thirdPartyId": 0,
    "totalSets": 0,
    "trainingLoad": 0,
    "type": 0,
    "unit": 0,
    "userId": "0",
    "version": 0,
    "videoCoverUrl": "",
    "videoUrl": "",
    "fastIntensityTypeName": "custom",
    "poolLengthId": 1,
    "poolLengthUnit": 2,
    "sourceId": "425706707117850624",
}

# Per-sport program-level differences (captured from the web builder's
# drafts): sportType, cover image source, and pbVersion (2 for running
# drafts, 5 for cycling drafts).
PROGRAM_SPORT_OVERRIDES = {
    "running": {
        "sportType": SPORT_TYPES["running"],
        "sourceId": "425706707117850624",
        "sourceUrl": (
            "https://d31oxp44ddzkyk.cloudfront.net/source/source_default/0/"
            "ee2ec19837ba4093b7c8617eb2f9b1f5.jpg"
        ),
        "pbVersion": 2,
    },
    "cycling": {
        "sportType": SPORT_TYPES["cycling"],
        "sourceId": "425868133463670784",
        "sourceUrl": (
            "https://d31oxp44ddzkyk.cloudfront.net/source/source_default/0/"
            "2fbd46e17bc54bc5873415c9fa767bdc.jpg"
        ),
        "pbVersion": 5,
    },
}
