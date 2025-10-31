from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime

class Teacher(BaseModel):
    teacher_id: str
    name: str

class TeacherAvailability(BaseModel):
    id: str
    teacher_id: str
    start_time: str  # ISO 8601, e.g., "2025-09-20T07:00:00.000000Z"
    end_time: str    # ISO 8601
    teacher_name: str

class TeacherBusyTime(BaseModel):
    id: str
    day_of_week: str
    start_time: str  # ISO 8601
    end_time: str    # ISO 8601
    teacher_id: str
    teacher_name: str

class TeacherCourses(BaseModel):
    id: str
    course_id: str
    teacher_id: str
    course_title: str
    course_credit: int
    course_code: str

class Hall(BaseModel):
    hall_id: str
    name: str

class HallBusyTime(BaseModel):
    id: str
    day_of_week: str
    start_time: str  # ISO 8601
    end_time: str    # ISO 8601
    hall_id: str
    hall_name: str

class ScheduleItem(BaseModel):
    id: str
    teacher_id: str
    teacher_name: str
    start_time: str  # ISO 8601
    end_time: str    # ISO 8601
    day_of_week: str
    duration: str
    course_id: str
    course_title: str
    course_code: str
    hall_id: str
    hall_name: str

class Constraints(BaseModel):
    course_duration: int = 60
    min_courses_per_day: int = 0
    max_courses_per_day: int = 8
    max_weekly_course_frequency: int = 5
    min_weekly_course_frequency: int = 1
    max_consecutive_classes: int = 3
    school_start_time: str = "08:00"  # HH:MM
    school_end_time: str = "16:00"    # HH:MM
    lesson_slot_length: int = 60
    max_daily_period_limit: int = 6
    min_daily_period_limit: int = 1
    time_gaps: bool = True
    max_weekly_load: int = 30 * 60
    min_weekly_load: int = 10 * 60
    equitable_distribution: bool = True
    lunch_break: bool = True
    lunch_break_start_time: str = "12:00"  # HH:MM
    lunch_break_end_time: str = "13:00"    # HH:MM

class SchedulingRequest(BaseModel):
    teachers: List[Teacher]
    teacher_busy_times: List[TeacherBusyTime] = []
    teacher_available_times: List[TeacherAvailability] = []
    teacher_courses: List[TeacherCourses] = []
    hall_busy_times: List[HallBusyTime] = []
    halls: List[Hall] = []
    constraints: Constraints = Constraints()

class SchedulingResponse(BaseModel):
    schedule: List[ScheduleItem]
    is_optimal: bool
    solution_info: str