from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Union, Literal, Any
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
    """Times when hall is unavailable (optionally per-day)."""
    hall_id: str
    hall_name: Optional[str] = ""
    start_time: str  # HH:MM format
    end_time: str
    day: Optional[str] = None  # If set, only this day is blocked; if omitted, applies to all days


# ===========================
# Break Period Configuration
# ===========================

class DayFixedBreak(BaseModel):
    """Custom break time for specific day"""
    day: str
    start_time: str
    end_time: str


class BreakConstraints(BaseModel):
    """Break period exceptions and overrides (doc: no_break_exceptions, day_exceptions)."""
    daysException: List[str] = []  # Days to skip default break (legacy)
    daysFixedBreaks: List[DayFixedBreak] = []  # Custom breaks per day (legacy)
    no_break_exceptions: Optional[List[str]] = None  # Doc: days where break is completely removed
    day_exceptions: Optional[List[DayFixedBreak]] = None  # Doc: day-specific break time overrides


class BreakPeriod(BaseModel):
    """Global break period configuration. Order: no_break_exceptions remove break, then day_exceptions override."""
    start_time: str
    end_time: str
    daily: Union[bool, str]  # Can be boolean or string "boolean"
    constrains: Optional[BreakConstraints] = None
    no_break_exceptions: Optional[List[str]] = None  # Top-level: days with no break
    day_exceptions: Optional[List[DayFixedBreak]] = None  # Top-level: per-day break overrides


# ===========================
# Operational Period Configuration
# ===========================

class OperationalConstraint(BaseModel):
    """Per-day operational hours override"""
    day: str
    start_time: str
    end_time: str


class OperationalPeriod(BaseModel):
    """Institution working hours configuration. Doc: day_exceptions = per-day overrides."""
    start_time: str
    end_time: str
    daily: Union[bool, str]  # Can be boolean or string "boolean"
    days: List[str]  # Active days of week
    constrains: List[OperationalConstraint] = []  # Per-day overrides (legacy)
    day_exceptions: Optional[List[OperationalConstraint]] = None  # Doc name: same as constrains


# ===========================
# Period Duration Configuration
# ===========================

class DayFixedPeriod(BaseModel):
    """Custom period duration for specific day"""
    day: str
    period: int  # Duration in minutes


class PeriodDayException(BaseModel):
    """Doc name: per-day duration override (day_exceptions[].duration_minutes)."""
    day: str
    duration_minutes: int


class PeriodConstraints(BaseModel):
    """Period duration exceptions and overrides"""
    daysException: List[str] = []  # Days to skip default period
    daysFixedPeriods: List[DayFixedPeriod] = []  # Custom periods per day
    day_exceptions: Optional[List[PeriodDayException]] = None  # Doc name: same idea as daysFixedPeriods


class Periods(BaseModel):
    """Configurable slot duration configuration. Doc: duration_minutes = default, day_exceptions = per-day."""
    daily: Union[bool, str] = True  # If true, apply uniform period to all days
    period: int = 30  # Default duration in minutes (legacy)
    duration_minutes: Optional[int] = None  # Doc name: same as period
    constrains: Optional[PeriodConstraints] = None
    day_exceptions: Optional[List[PeriodDayException]] = None  # Doc name: per-day duration overrides


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


class TeacherMaxHoursException(BaseModel):
    """Override max hours for a specific teacher (soft constraint)."""
    teacher_id: str
    max_hours: Union[int, float]


class SoftConstraints(BaseModel):
    """Comprehensive soft constraints configuration (mocks/constraints/softconstraints.json)."""
    
    # Teacher constraints (accept number or dict with max_hours + teacher_exceptions)
    teacher_max_daily_hours: Union[float, int, str, Dict[str, Any], None] = None
    teacher_max_weekly_hours: Union[float, int, str, Dict[str, Any], None] = None
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
    
    # Time constraints (schedule_max_periods_per_day, schedule_max_free_periods_per_day from doc/mocks)
    time_max_periods_per_day: Union[int, str, Dict[str, Any], None] = None
    time_min_free_periods_per_day: Union[int, str, Dict[str, Any], None] = None
    schedule_max_periods_per_day: Union[int, str, Dict[str, Any], None] = None
    schedule_max_free_periods_per_day: Union[int, str, Dict[str, Any], None] = None
    course_max_daily_frequency: Union[int, str, Dict[str, Any], None] = None
    # Requested placement (soft): teacher/hall/course windows, requested_assignments, requested_free_periods
    teacher_requested_time_windows: Optional[List[Dict[str, Any]]] = None
    hall_requested_time_windows: Optional[List[Dict[str, Any]]] = None
    course_requested_time_slots: Optional[List[Dict[str, Any]]] = None
    requested_assignments: Optional[List[Dict[str, Any]]] = None
    requested_free_periods: Optional[List[Dict[str, Any]]] = None
    time_balanced_daily_workload: Union[bool, str] = False
    time_balanced_weekly_workload: Union[bool, str] = False
    time_avoid_consecutive_heavy_subjects: Union[bool, str] = False
    time_consecutive_period_allowance: Optional[Union[TimeConsecutivePeriodAllowance, Dict]] = None
    time_min_gap_between_sessions: Union[float, str, None] = None
    time_subject_frequency_per_day: Union[int, str, None] = None


# ===========================
# Required Joint Course Periods (hard constraint)
# ===========================


class RequiredJointPeriodItem(BaseModel):
    """One locked period: exact day and time."""
    day: str
    start_time: str
    end_time: str


class RequiredJointCoursePeriods(BaseModel):
    """Locked placements: course + teacher must appear at these exact periods."""
    course_id: str
    teacher_id: str
    periods: List[RequiredJointPeriodItem]


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
    periods: Optional[Periods] = None  # Optional slot duration configuration
    soft_constrains: SoftConstraints = SoftConstraints()
    required_joint_course_periods: List[RequiredJointCoursePeriods] = []


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


class AffectedEntity(BaseModel):
    """Entity affected by an error or constraint violation"""
    entity_type: str  # "TEACHER", "COURSE", "HALL", "TIME_SLOT", etc.
    teacher_id: Optional[str] = None
    teacher_name: Optional[str] = None
    course_id: Optional[str] = None
    course_name: Optional[str] = None
    hall_id: Optional[str] = None
    hall_name: Optional[str] = None
    day: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None


class RootCause(BaseModel):
    """Root cause of an error or constraint violation"""
    cause: str
    details: Optional[str] = None


class ErrorMessage(BaseModel):
    """Error or warning message with detailed diagnostics"""
    constraint_type: str = "HARD"  # "HARD" or "SOFT"
    severity: str = "ERROR"  # "ERROR" or "WARNING"
    code: str  # Stable unique error code (e.g., "TEACHER_BUSY_PERIOD_CONFLICT")
    title: str
    description: str  # Detailed description (was "message")
    affected_entities: List[AffectedEntity] = []
    root_causes: List[RootCause] = []
    resolution_hint: Optional[str] = None


class Messages(BaseModel):
    """Collection of error/warning messages (legacy; prefer diagnostics)."""
    error_message: List[ErrorMessage] = []


# ===========================
# Diagnostics (DR-01 to DR-05)
# ===========================


class DiagnosticBlocker(BaseModel):
    """Single blocker: type, entity, conflict, evidence (DR-03)."""
    type: str  # e.g. TEACHER_MAX_DAILY_HOURS_EXCEEDED, HALL_BUSY
    entity: Optional[Dict[str, Any]] = None  # e.g. {"type": "TEACHER", "id": "...", "name": "..."}
    conflict: Optional[Dict[str, Any]] = None  # quantitative/structural description
    evidence: Optional[Dict[str, Any]] = None  # booked_slots, busy_slots, etc.


class ConstraintFailure(BaseModel):
    """One failed constraint entry: constraint_failed, blockers, suggestions (DR-02)."""
    constraint_failed: Dict[str, Any]  # {"type": "...", "details": {...}}
    blockers: List[DiagnosticBlocker] = []
    suggestions: List[Dict[str, Any]] = []


class DiagnosticsConstraints(BaseModel):
    """Grouped diagnostics: hard and soft arrays (DR-01)."""
    hard: List[ConstraintFailure] = []
    soft: List[ConstraintFailure] = []


class DiagnosticsSummary(BaseModel):
    """Summary consistent with status (RC-04)."""
    message: str
    hard_constraints_met: bool
    soft_constraints_met: bool
    failed_soft_constraints_count: int = 0
    failed_hard_constraints_count: int = 0


class Diagnostics(BaseModel):
    """Full diagnostics payload."""
    constraints: DiagnosticsConstraints = Field(default_factory=DiagnosticsConstraints)
    summary: DiagnosticsSummary


class ResponseMetadata(BaseModel):
    """Response metadata (solve time, etc.)."""
    solve_time_seconds: float = 0.0


class SchedulingResponse(BaseModel):
    """Complete scheduling response matching API contract and functional spec."""
    status: str  # OPTIMAL | PARTIAL | ERROR (RC-01, RC-02, RC-03)
    timetable: List[DaySchedule] = []
    diagnostics: Diagnostics = Field(default_factory=lambda: Diagnostics(
        constraints=DiagnosticsConstraints(hard=[], soft=[]),
        summary=DiagnosticsSummary(
            message="All constraints satisfied.",
            hard_constraints_met=True,
            soft_constraints_met=True,
        ),
    ))
    metadata: ResponseMetadata = Field(default_factory=ResponseMetadata)

    # Legacy: keep for backward compatibility; may be populated from diagnostics
    messages: Messages = Messages()
    solve_time_seconds: Optional[float] = None