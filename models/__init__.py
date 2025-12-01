"""
Data models and Pydantic schemas for the scheduling API.
"""
from .schemas import (
    Teacher,
    TeacherBusyPeriod,
    TeacherPreferredTeachingPeriod,
    TeacherCourse,
    Hall,
    HallBusyPeriod,
    BreakPeriod,
    OperationalPeriod,
    SoftConstraints,
    SchedulingRequest,
    ScheduleSlot,
    DaySchedule,
    Messages,
    ErrorMessage,
    SchedulingResponse
)

__all__ = [
    "Teacher",
    "TeacherBusyPeriod",
    "TeacherPreferredTeachingPeriod",
    "TeacherCourse",
    "Hall",
    "HallBusyPeriod",
    "BreakPeriod",
    "OperationalPeriod",
    "SoftConstraints",
    "SchedulingRequest",
    "ScheduleSlot",
    "DaySchedule",
    "Messages",
    "ErrorMessage",
    "SchedulingResponse"
]
