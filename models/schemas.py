from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Union, Literal
from datetime import datetime


# ===========================
# Teacher Models
# ===========================

class Teacher(BaseModel):
    teacher_id: str
    name: str


class TeacherPreferredTeachingPeriod(BaseModel):
    """Teacher's preferred time slots for teaching (soft constraint)"""
    start_time: str  # HH:MM format, e.g., "14:00"
    end_time: str    # HH:MM format, e.g., "18:00"
    day: str         # lowercase: "monday", "tuesday", etc.
    teacher_id: str
    teacher_name: str


class TeacherBusyPeriod(BaseModel):
    """Times when teacher is unavailable (hard constraint)"""
    start_time: str  # HH:MM format
    end_time: str
    day: str         # lowercase: "monday", "tuesday", etc.
    teacher_id: str
    teacher_name: str
    course_id: Optional[str] = ""
    course_code: Optional[str] = ""


class TeacherCourse(BaseModel):
    """Courses assigned to teachers"""
    course_id: str
    course_title: str
    course_credit: int           # Weight/importance of course
    course_type: str             # "theory" or "practical"
    course_hours: int            # Total hours needed per semester/term
    teacher_id: str
    teacher_name: str


# ===========================
# Hall Models
# ===========================

class Hall(BaseModel):
    hall_name: str
    hall_id: str
    hall_capacity: int
    hall_type: str  # "lab" or "lecture"


class HallBusyPeriod(BaseModel):
    """Times when hall is unavailable"""
    hall_id: str
    hall_name: Optional[str] = ""
    start_time: str  # HH:MM format
    end_time: str


# ===========================
# Break Period Configuration
# ===========================

class DayFixedBreak(BaseModel):
    """Custom break time for specific day"""
    day: str
    start_time: str
    end_time: str


class BreakConstraints(BaseModel):
    """Break period exceptions and overrides"""
    daysException: List[str] = []  # Days to skip default break
    daysFixedBreaks: List[DayFixedBreak] = []  # Custom breaks per day


class BreakPeriod(BaseModel):
    """Global break period configuration"""
    start_time: str
    end_time: str
    daily: Union[bool, str]  # Can be boolean or string "boolean"
    constrains: Optional[BreakConstraints] = None


# ===========================
# Operational Period Configuration
# ===========================

class OperationalConstraint(BaseModel):
    """Per-day operational hours override"""
    day: str
    start_time: str
    end_time: str


class OperationalPeriod(BaseModel):
    """Institution working hours configuration"""
    start_time: str
    end_time: str
    daily: Union[bool, str]  # Can be boolean or string "boolean"
    days: List[str]  # Active days of week
    constrains: List[OperationalConstraint] = []  # Per-day overrides


# ===========================
# Soft Constraints Configuration
# ===========================

class CourseRoomSuitability(BaseModel):
    """Mapping of course types to hall types"""
    theory: str = "lecture"
    practical: str = "lab"


class CoursePreferredTimeOfDay(BaseModel):
    """Preferred time slots for course types"""
    theory: str = "morning"  # "morning" or "evening"
    practical: str = "evening"


class HallTypeSuitability(BaseModel):
    """Hall type matching rules"""
    theory: str = "lecture"
    practical: str = "lab"


class TimeConsecutivePeriodAllowance(BaseModel):
    """Rules for consecutive period scheduling"""
    practicals: Union[bool, str]
    theory: Union[bool, str]


class SoftConstraints(BaseModel):
    """Comprehensive soft constraints configuration"""
    
    # Teacher constraints
    teacher_max_daily_hours: Union[float, str, None] = None
    teacher_max_weekly_hours: Union[float, str, None] = None
    teacher_minimum_break_between_classes: Union[int, str, None] = None
    teacher_even_subject_distribution: Union[bool, str] = False
    teacher_balanced_workload: Union[bool, str] = False
    teacher_avoid_split_double_periods: Union[bool, str] = False
    
    # Course constraints
    course_load_proportionality: Union[bool, str] = False
    course_avoid_clustering: Union[bool, str] = False
    course_minimum_gap_between_sessions: Union[bool, str, None] = None
    course_room_suitability: Optional[Union[CourseRoomSuitability, Dict]] = None
    course_preferred_time_of_day: Optional[Union[CoursePreferredTimeOfDay, Dict]] = None
    course_credit_hour_density_control: Union[bool, str] = False
    course_spread_across_week: Union[bool, str] = False
    
    # Hall constraints
    hall_capacity_limit: Union[bool, str] = False
    hall_type_suitability: Optional[Union[HallTypeSuitability, Dict]] = None
    hall_change_minimization: Union[bool, str] = False
    hall_usage_balance: Union[bool, str] = False
    
    # Time constraints
    time_max_periods_per_day: Union[int, str, None] = None
    time_min_free_periods_per_day: Union[int, str, None] = None
    time_balanced_daily_workload: Union[bool, str] = False
    time_balanced_weekly_workload: Union[bool, str] = False
    time_avoid_consecutive_heavy_subjects: Union[bool, str] = False
    time_consecutive_period_allowance: Optional[Union[TimeConsecutivePeriodAllowance, Dict]] = None
    time_min_gap_between_sessions: Union[float, str, None] = None
    time_subject_frequency_per_day: Union[int, str, None] = None


# ===========================
# Request Schema
# ===========================

class SchedulingRequest(BaseModel):
    """Complete scheduling request matching API contract"""
    teacher_prefered_teaching_period: List[TeacherPreferredTeachingPeriod] = []
    teachers: List[Teacher]
    teacher_busy_period: List[TeacherBusyPeriod] = []
    teacher_courses: List[TeacherCourse] = []
    halls: List[Hall] = []
    hall_busy_periods: List[HallBusyPeriod] = []
    break_period: BreakPeriod
    operational_period: OperationalPeriod
    soft_constrains: SoftConstraints = SoftConstraints()


# ===========================
# Response Schema
# ===========================

class ScheduleSlot(BaseModel):
    """Individual time slot in the timetable"""
    day: str
    start_time: str
    end_time: str
    break_: bool = Field(alias="break")  # "break" is Python keyword
    duration: Optional[str] = None  # Human-readable: "2h 30min"
    teacher_id: Optional[str] = None
    teacher_name: Optional[str] = None
    course_id: Optional[str] = None
    course_name: Optional[str] = None  # Note: "course_name" not "course_title"
    hall_id: Optional[str] = None
    hall_name: Optional[str] = None

    class Config:
        populate_by_name = True  # Allow both "break" and "break_"


class DaySchedule(BaseModel):
    """Schedule for a single day"""
    day: str
    slots: List[ScheduleSlot]


class ErrorMessage(BaseModel):
    """Error or warning message"""
    title: str
    message: str


class Messages(BaseModel):
    """Collection of error/warning messages"""
    error_message: List[ErrorMessage] = []


class SchedulingResponse(BaseModel):
    """Complete scheduling response matching API contract"""
    timetable: List[DaySchedule]
    messages: Messages = Messages()
    
    # Additional metadata for debugging
    status: Optional[str] = None  # "OPTIMAL", "FEASIBLE", "INFEASIBLE", "TIMEOUT"
    solve_time_seconds: Optional[float] = None