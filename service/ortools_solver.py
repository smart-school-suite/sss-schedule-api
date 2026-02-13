"""
OR-Tools CP-SAT based scheduling solver.

This module implements a comprehensive constraint satisfaction and optimization
solver for school timetabling using Google OR-Tools CP-SAT solver.
"""

from ortools.sat.python import cp_model
from typing import List, Dict, Tuple, Optional, Set
from models.schemas import (
    SchedulingRequest, SchedulingResponse, DaySchedule, ScheduleSlot,
    Messages, ErrorMessage, AffectedEntity, RootCause,
    Diagnostics, DiagnosticsConstraints, DiagnosticsSummary, ResponseMetadata,
    ConstraintFailure, DiagnosticBlocker,
    RequiredJointCoursePeriods,
)
from datetime import datetime, time, timedelta
import logging

logger = logging.getLogger(__name__)


class ORToolsScheduler:
    """
    Constraint-based scheduler using OR-Tools CP-SAT solver.
    
    Supports both preference-based and non-preference scheduling modes.
    """
    
    def __init__(self, respect_preferences: bool = True, time_limit_seconds: int = 30):
        """
        Initialize the scheduler.
        
        Args:
            respect_preferences: If True, considers teacher preferred teaching periods
            time_limit_seconds: Maximum time allowed for solver
        """
        self.respect_preferences = respect_preferences
        self.time_limit_seconds = time_limit_seconds
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        
        # Solver parameters for deterministic behavior
        self.solver.parameters.random_seed = 42
        self.solver.parameters.num_search_workers = 1
        self.solver.parameters.max_time_in_seconds = time_limit_seconds
        
        # Data structures
        self.request: Optional[SchedulingRequest] = None
        self.days: List[str] = []
        self.slots_per_day: Dict[str, List[int]] = {}  # day -> list of slot indices
        self.slot_times: Dict[str, Dict[int, Tuple[str, str]]] = {}  # day -> slot -> (start, end)
        self.variables: Dict = {}
        self.errors: List[ErrorMessage] = []
        # Diagnostics (DR-01): collected during solve for response
        self._hard_failures: List[ConstraintFailure] = []
        self._soft_failures: List[ConstraintFailure] = []
        
    def solve_scheduling(self, request: SchedulingRequest) -> SchedulingResponse:
        """
        Main entry point to solve the scheduling problem.
        
        Args:
            request: The scheduling request with all data and constraints
            
        Returns:
            SchedulingResponse with timetable or error messages
        """
        self.request = request
        self.errors = []
        self._hard_failures = []
        self._soft_failures = []

        try:
            # Step 1: Parse and validate operational periods
            self._parse_operational_periods()
            
            # Step 2: Build time slots for each day
            self._build_time_slots()
            
            # Step 3: Validate input data
            validation_errors = self._validate_input()
            if validation_errors:
                return self._create_infeasible_response(validation_errors)
            
            # Step 4: Create decision variables
            self._create_variables()
            
            # Step 5: Add hard constraints
            self._add_hard_constraints()
            required_failures = self._add_required_joint_period_constraints()
            if required_failures:
                return self._build_response("ERROR", [], 0.0, hard_failures=required_failures, soft_failures=[])

            # Step 6: Add soft constraints and objective
            self._add_soft_constraints_and_objective()
            
            # Step 7: Solve the model
            start_time = datetime.now()
            status = self.solver.Solve(self.model)
            solve_time = (datetime.now() - start_time).total_seconds()
            
            # Step 8: Extract and return solution
            return self._extract_solution(status, solve_time)
            
        except Exception as e:
            logger.error(f"Scheduling error: {str(e)}", exc_info=True)
            return self._create_error_response(str(e))
    
    def _parse_operational_periods(self):
        """Parse operational period configuration and determine active days."""
        op_period = self.request.operational_period
        
        # Determine active days
        self.days = [d.lower() for d in op_period.days]
        
        # Parse operational hours per day
        self.operational_hours = {}
        
        # Check if using global or per-day configuration
        use_daily = self._parse_bool(op_period.daily)
        
        if use_daily:
            # Use same hours for all days
            for day in self.days:
                self.operational_hours[day] = (op_period.start_time, op_period.end_time)
        
        # Apply per-day overrides
        for constraint in op_period.constrains:
            day = constraint.day.lower()
            if day in self.days:
                self.operational_hours[day] = (constraint.start_time, constraint.end_time)
        
        # Set default if not configured
        for day in self.days:
            if day not in self.operational_hours:
                self.operational_hours[day] = (op_period.start_time, op_period.end_time)
    
    def _build_time_slots(self):
        """Build discrete time slots for each day; align to 15-min boundaries (00, 15, 30, 45)."""
        for day in self.days:
            period_duration = self._get_period_duration(day)
            start_str, end_str = self.operational_hours[day]
            start_time = self._parse_time(start_str)
            end_time = self._parse_time(end_str)

            # Align first slot start to next 15-min boundary (functional spec: standardized time slot alignment)
            start_time = self._align_time_to_quarter_hour(start_time)
            if start_time >= end_time:
                self.slots_per_day[day] = []
                self.slot_times[day] = {}
                continue

            slots = []
            slot_times = {}
            current_time = start_time
            slot_idx = 0

            while current_time < end_time:
                next_time = self._add_minutes(current_time, period_duration)
                if next_time > end_time:
                    break
                slots.append(slot_idx)
                slot_times[slot_idx] = (
                    self._time_to_str(current_time),
                    self._time_to_str(next_time),
                )
                current_time = next_time
                slot_idx += 1

            self.slots_per_day[day] = slots
            self.slot_times[day] = slot_times
    
    def _get_period_duration(self, day: str) -> int:
        """
        Get period duration in minutes for a specific day.
        
        Logic:
        1. If periods config exists and day has fixed period, use that
        2. If periods config exists and daily is true, use default period
        3. Otherwise, default to 30 minutes
        """
        if not self.request.periods:
            return 30  # Default 30 minutes
        
        periods_config = self.request.periods
        
        # Check for fixed period on this specific day
        if periods_config.constrains and periods_config.constrains.daysFixedPeriods:
            for fixed_period in periods_config.constrains.daysFixedPeriods:
                if fixed_period.day.lower() == day:
                    return fixed_period.period
        
        # Use default period if daily is true
        use_daily = self._parse_bool(periods_config.daily)
        if use_daily:
            return periods_config.period
        
        # Fallback to default
        return 30
    
    def _validate_input(self) -> List[str]:
        """Validate input data and return list of errors."""
        errors = []
        
        if not self.request.teachers:
            errors.append("No teachers provided")
        
        if not self.request.teacher_courses:
            errors.append("No courses provided")
        
        if not self.request.halls:
            errors.append("No halls provided")
        
        # Validate course-teacher assignments
        teacher_ids = {t.teacher_id for t in self.request.teachers}
        for course in self.request.teacher_courses:
            if course.teacher_id not in teacher_ids:
                errors.append(f"Course {course.course_title} assigned to unknown teacher {course.teacher_id}")
        
        # Validate hall types
        valid_hall_types = {"lecture", "lab"}
        for hall in self.request.halls:
            if hall.hall_type not in valid_hall_types:
                errors.append(f"Hall {hall.hall_name} has invalid type: {hall.hall_type}")
        
        # Validate course types
        valid_course_types = {"theory", "practical"}
        for course in self.request.teacher_courses:
            if course.course_type.lower() not in valid_course_types:
                errors.append(f"Course {course.course_title} has invalid type: {course.course_type}")
        
        # Validate break period
        errors.extend(self._validate_break_period())
        
        # Validate periods configuration
        if self.request.periods:
            errors.extend(self._validate_periods())
        
        # Validate teacher busy periods
        errors.extend(self._validate_teacher_busy_periods())
        
        # Validate teacher preferred periods
        errors.extend(self._validate_teacher_preferred_periods())
        
        return errors
    
    def _validate_break_period(self) -> List[str]:
        """Validate break period configuration."""
        errors = []
        break_config = self.request.break_period
        
        # Validate time format and order
        try:
            start_time = self._parse_time(break_config.start_time)
            end_time = self._parse_time(break_config.end_time)
            
            if start_time >= end_time:
                errors.append(f"Break period start time ({break_config.start_time}) must be before end time ({break_config.end_time})")
        except ValueError:
            errors.append(f"Invalid break period time format. Use HH:MM format (e.g., '12:00')")
        
        valid_days = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
        def validate_day_list(days, label):
            for day in days or []:
                d = day.lower() if hasattr(day, "lower") else str(day).lower()
                if d not in valid_days:
                    errors.append(f"Invalid day in {label}. Use valid weekdays.")
        def validate_fixed_breaks(breaks, label):
            for fixed_break in breaks or []:
                day = getattr(fixed_break, "day", fixed_break.get("day") if isinstance(fixed_break, dict) else "")
                if str(day).lower() not in valid_days:
                    errors.append(f"Invalid day in {label}. Use valid weekdays.")
                try:
                    s = getattr(fixed_break, "start_time", fixed_break.get("start_time"))
                    e = getattr(fixed_break, "end_time", fixed_break.get("end_time"))
                    if s and e:
                        fb_start = self._parse_time(s)
                        fb_end = self._parse_time(e)
                        if fb_start >= fb_end:
                            errors.append(f"Fixed break for {day}: start time must be before end time")
                except (ValueError, TypeError):
                    errors.append(f"Invalid time format in {label}. Use HH:MM format.")
        no_break = getattr(break_config, "no_break_exceptions", None)
        day_exc = getattr(break_config, "day_exceptions", None)
        validate_day_list(no_break, "no_break_exceptions")
        validate_fixed_breaks(day_exc, "day_exceptions")
        if break_config.constrains:
            validate_day_list(break_config.constrains.daysException, "daysException")
            validate_fixed_breaks(break_config.constrains.daysFixedBreaks, "daysFixedBreaks")
            if break_config.constrains.no_break_exceptions:
                validate_day_list(break_config.constrains.no_break_exceptions, "constrains.no_break_exceptions")
            if break_config.constrains.day_exceptions:
                validate_fixed_breaks(break_config.constrains.day_exceptions, "constrains.day_exceptions")
        return errors
    
    def _validate_periods(self) -> List[str]:
        """Validate periods configuration."""
        errors = []
        periods_config = self.request.periods
        
        if periods_config.period <= 0:
            errors.append("Period duration must be greater than 0 minutes")
        
        if periods_config.constrains:
            valid_days = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
            
            # Validate days_exception
            for day in periods_config.constrains.daysException:
                if day.lower() not in valid_days:
                    errors.append(f"Invalid day '{day}' in periods days_exception")
            
            # Validate days_fixed_periods
            for fixed_period in periods_config.constrains.daysFixedPeriods:
                if fixed_period.day.lower() not in valid_days:
                    errors.append(f"Invalid day '{fixed_period.day}' in days_fixed_periods")
                if fixed_period.period <= 0:
                    errors.append(f"Period duration for {fixed_period.day} must be greater than 0 minutes")
        
        return errors
    
    def _validate_teacher_busy_periods(self) -> List[str]:
        """Validate teacher busy periods."""
        errors = []
        valid_days = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
        
        for busy_period in self.request.teacher_busy_period:
            if busy_period.day.lower() not in valid_days:
                errors.append(f"Invalid day '{busy_period.day}' in teacher busy period for {busy_period.teacher_name}")
            
            try:
                start_time = self._parse_time(busy_period.start_time)
                end_time = self._parse_time(busy_period.end_time)
                if start_time >= end_time:
                    errors.append(f"Teacher {busy_period.teacher_name} busy period: start time must be before end time")
            except ValueError:
                errors.append(f"Invalid time format in busy period for {busy_period.teacher_name}")
        
        return errors
    
    def _validate_teacher_preferred_periods(self) -> List[str]:
        """Validate teacher preferred teaching periods."""
        errors = []
        valid_days = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
        
        for pref_period in self.request.teacher_prefered_teaching_period:
            if pref_period.day.lower() not in valid_days:
                errors.append(f"Invalid day '{pref_period.day}' in preferred teaching period for {pref_period.teacher_name}")
            
            try:
                start_time = self._parse_time(pref_period.start_time)
                end_time = self._parse_time(pref_period.end_time)
                if start_time >= end_time:
                    errors.append(f"Teacher {pref_period.teacher_name} preferred period: start time must be before end time")
            except ValueError:
                errors.append(f"Invalid time format in preferred period for {pref_period.teacher_name}")
        
        return errors
    
    def _create_variables(self):
        """Create decision variables for the CP-SAT model."""
        # Variables: x[course_idx][day][slot][hall_idx] = 1 if course is scheduled
        self.variables = {}
        
        for course_idx, course in enumerate(self.request.teacher_courses):
            self.variables[course_idx] = {}
            
            # Calculate how many sessions needed per week
            sessions_needed = self._calculate_sessions_per_week(course)
            self.variables[course_idx]['sessions_needed'] = sessions_needed
            self.variables[course_idx]['assignment'] = {}
            
            for day in self.days:
                self.variables[course_idx]['assignment'][day] = {}
                
                for slot in self.slots_per_day[day]:
                    self.variables[course_idx]['assignment'][day][slot] = {}
                    
                    # Filter halls by course type suitability
                    suitable_halls = self._get_suitable_halls(course)
                    
                    for hall_idx, hall in enumerate(suitable_halls):
                        # Check if slot is feasible for teacher and hall
                        if self._is_slot_feasible(course, day, slot, hall):
                            var = self.model.NewBoolVar(
                                f'course_{course_idx}_day_{day}_slot_{slot}_hall_{hall_idx}'
                            )
                            self.variables[course_idx]['assignment'][day][slot][hall.hall_id] = var
    
    def _add_hard_constraints(self):
        """Add all hard constraints to the model."""
        
        # 1. Course frequency constraint: each course scheduled correct number of times
        for course_idx in self.variables:
            if course_idx == 'sessions_needed':
                continue
                
            sessions_needed = self.variables[course_idx]['sessions_needed']
            all_assignments = []
            
            for day in self.days:
                for slot in self.slots_per_day[day]:
                    for hall_id in self.variables[course_idx]['assignment'][day].get(slot, {}):
                        var = self.variables[course_idx]['assignment'][day][slot][hall_id]
                        all_assignments.append(var)
            
            if all_assignments:
                # Each course must be scheduled exactly sessions_needed times
                self.model.Add(sum(all_assignments) == sessions_needed)
        
        # 2. No teacher double-booking: teacher can teach max 1 course per slot
        teacher_to_courses = self._build_teacher_course_map()
        
        for teacher_id, course_indices in teacher_to_courses.items():
            for day in self.days:
                for slot in self.slots_per_day[day]:
                    slot_assignments = []
                    
                    for course_idx in course_indices:
                        for hall_id in self.variables[course_idx]['assignment'][day].get(slot, {}):
                            var = self.variables[course_idx]['assignment'][day][slot][hall_id]
                            slot_assignments.append(var)
                    
                    if slot_assignments:
                        # At most 1 course for this teacher in this slot
                        self.model.Add(sum(slot_assignments) <= 1)
        
        # 3. No hall double-booking: each hall used by max 1 course per slot
        for day in self.days:
            for slot in self.slots_per_day[day]:
                for hall in self.request.halls:
                    hall_assignments = []
                    
                    for course_idx in self.variables:
                        if course_idx == 'sessions_needed':
                            continue
                        
                        if hall.hall_id in self.variables[course_idx]['assignment'][day].get(slot, {}):
                            var = self.variables[course_idx]['assignment'][day][slot][hall.hall_id]
                            hall_assignments.append(var)
                    
                    if hall_assignments:
                        # At most 1 course in this hall at this slot
                        self.model.Add(sum(hall_assignments) <= 1)

        # 4. Required joint course periods: fix assignments at exact (day, start_time, end_time)
        # (validation and constraint addition done in _add_required_joint_period_constraints)

    def _find_slot_index(self, day: str, start_time_str: str, end_time_str: str) -> Optional[int]:
        """Return slot index for (day, start_time, end_time) or None if no matching slot."""
        day = day.lower()
        if day not in self.slot_times:
            return None
        for slot, (s_start, s_end) in self.slot_times[day].items():
            if s_start == start_time_str and s_end == end_time_str:
                return slot
        return None

    def _add_required_joint_period_constraints(self) -> List[ConstraintFailure]:
        """Validate required joint periods and add var==1 constraints. Return list of hard failures if any."""
        failures: List[ConstraintFailure] = []
        if not getattr(self.request, "required_joint_course_periods", None):
            return failures

        for item in self.request.required_joint_course_periods:
            course_idx = None
            for idx, c in enumerate(self.request.teacher_courses):
                if c.course_id == item.course_id and c.teacher_id == item.teacher_id:
                    course_idx = idx
                    break
            if course_idx is None:
                failures.append(ConstraintFailure(
                    constraint_failed={
                        "type": "REQUIRED_JOINT_COURSE_PERIODS",
                        "details": {
                            "course_id": item.course_id,
                            "teacher_id": item.teacher_id,
                            "reason": "course_id and teacher_id do not match any teacher_courses entry",
                        },
                    },
                    blockers=[
                        DiagnosticBlocker(
                            type="TEACHER_COURSE_MISMATCH",
                            entity={"type": "COURSE", "course_id": item.course_id, "teacher_id": item.teacher_id},
                            conflict={"reason": "No matching teacher_courses entry"},
                            evidence={},
                        )
                    ],
                    suggestions=[],
                ))
                continue

            if course_idx not in self.variables or "assignment" not in self.variables[course_idx]:
                continue

            for period in item.periods:
                day = period.day.lower()
                slot = self._find_slot_index(day, period.start_time, period.end_time)
                if slot is None:
                    failures.append(ConstraintFailure(
                        constraint_failed={
                            "type": "REQUIRED_JOINT_COURSE_PERIODS",
                            "details": {
                                "course_id": item.course_id,
                                "teacher_id": item.teacher_id,
                                "day": period.day,
                                "start_time": period.start_time,
                                "end_time": period.end_time,
                                "reason": "No slot matches this exact time; check period duration and operational hours.",
                            },
                        },
                        blockers=[
                            DiagnosticBlocker(
                                type="SLOT_NOT_FOUND",
                                conflict={
                                    "day": period.day,
                                    "start_time": period.start_time,
                                    "end_time": period.end_time,
                                },
                                evidence={"message": "No slot with this exact start/end time in the grid."},
                            )
                        ],
                        suggestions=[],
                    ))
                    continue

                # Find any feasible hall for this (course_idx, day, slot)
                halls_here = self.variables[course_idx]["assignment"].get(day, {}).get(slot, {})
                if not halls_here:
                    failures.append(ConstraintFailure(
                        constraint_failed={
                            "type": "REQUIRED_JOINT_COURSE_PERIODS",
                            "details": {
                                "course_id": item.course_id,
                                "teacher_id": item.teacher_id,
                                "day": period.day,
                                "start_time": period.start_time,
                                "end_time": period.end_time,
                                "reason": "No feasible hall at this slot (teacher busy, hall busy, or break).",
                            },
                        },
                        blockers=[
                            DiagnosticBlocker(
                                type="HALL_UNAVAILABLE",
                                conflict={"day": period.day, "start_time": period.start_time, "end_time": period.end_time},
                                evidence={},
                            )
                        ],
                        suggestions=[],
                    ))
                    continue

                # Pick first available hall and fix assignment
                hall_id = next(iter(halls_here))
                var = self.variables[course_idx]["assignment"][day][slot][hall_id]
                self.model.Add(var == 1)

        return failures

    def _add_soft_constraints_and_objective(self):
        """Add soft constraints as weighted objectives."""
        objective_terms = []
        
        # If respecting preferences, add bonus for matching preferred times
        if self.respect_preferences and self.request.teacher_prefered_teaching_period:
            for pref in self.request.teacher_prefered_teaching_period:
                teacher_courses = [
                    idx for idx, course in enumerate(self.request.teacher_courses)
                    if course.teacher_id == pref.teacher_id
                ]
                
                day = pref.day.lower()
                if day not in self.days:
                    continue
                
                # Find slots that overlap with preference
                pref_start = self._parse_time(pref.start_time)
                pref_end = self._parse_time(pref.end_time)
                
                for course_idx in teacher_courses:
                    for slot in self.slots_per_day[day]:
                        slot_start_str, slot_end_str = self.slot_times[day][slot]
                        slot_start = self._parse_time(slot_start_str)
                        
                        # Check if slot is within preferred period
                        if pref_start <= slot_start < pref_end:
                            for hall_id in self.variables[course_idx]['assignment'][day].get(slot, {}):
                                var = self.variables[course_idx]['assignment'][day][slot][hall_id]
                                objective_terms.append(var * 10)  # Weight: 10 points per match
        
        # Objective: Maximize preference matches
        if objective_terms:
            self.model.Maximize(sum(objective_terms))
    
    def _extract_solution(self, status, solve_time: float) -> SchedulingResponse:
        """Extract solution from solver and format response."""
        if status == cp_model.INFEASIBLE:
            return self._create_infeasible_response(["No feasible schedule exists. Try relaxing constraints or adding more halls/time slots."])
        
        if status == cp_model.UNKNOWN:
            return self._create_error_response("Solver timeout - no solution found within time limit")
        
        # Extract assigned courses
        timetable = []
        
        for day in self.days:
            day_slots = []
            
            # Collect all scheduled slots for this day
            scheduled_slots = {}  # slot_idx -> list of slot objects
            
            for course_idx, course in enumerate(self.request.teacher_courses):
                if course_idx not in self.variables:
                    continue
                
                for slot in self.slots_per_day[day]:
                    for hall_id, var in self.variables[course_idx]['assignment'][day].get(slot, {}).items():
                        if self.solver.Value(var) == 1:
                            # This course is scheduled at this slot and hall
                            hall = next((h for h in self.request.halls if h.hall_id == hall_id), None)
                            teacher = next((t for t in self.request.teachers if t.teacher_id == course.teacher_id), None)
                            
                            if not hall or not teacher:
                                continue
                            
                            slot_start, slot_end = self.slot_times[day][slot]
                            duration_str = self._format_duration(slot_start, slot_end)
                            
                            schedule_slot = ScheduleSlot(
                                day=day.capitalize(),
                                start_time=slot_start,
                                end_time=slot_end,
                                teacher_id=teacher.teacher_id,
                                teacher_name=teacher.name,
                                course_id=course.course_id,
                                course_name=course.course_title,
                                hall_id=hall.hall_id,
                                hall_name=hall.hall_name,
                                break_=False,
                                duration=duration_str
                            )
                            
                            if slot not in scheduled_slots:
                                scheduled_slots[slot] = []
                            scheduled_slots[slot].append(schedule_slot)
            
            # Sort by slot index and flatten
            for slot_idx in sorted(scheduled_slots.keys()):
                day_slots.extend(scheduled_slots[slot_idx])
            
            # Count non-break slots (actual classes)
            non_break_slots_count = len(day_slots)
            
            # Add break slots
            break_slots = self._get_break_slots(day)
            day_slots.extend(break_slots)
            
            # Exclude days that have only break slots (no actual classes)
            if non_break_slots_count == 0:
                continue  # Skip this day - no classes scheduled
            
            # Sort all slots by start time
            day_slots.sort(key=lambda s: s.start_time)
            
            day_schedule = DaySchedule(day=day.capitalize(), slots=day_slots)
            timetable.append(day_schedule)

        # Post-solve soft constraint checks (teacher max daily/weekly hours, etc.)
        self._check_soft_constraints(timetable)
        
        # RC-01: all hard and soft satisfied -> OPTIMAL; RC-02: hard met, soft failed -> PARTIAL (spec: no FEASIBLE)
        status_str = "OPTIMAL" if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) else "OPTIMAL"
        if self._soft_failures:
            status_str = "PARTIAL"
        return self._build_response(status_str, timetable, solve_time, hard_failures=[], soft_failures=self._soft_failures)
    
    # ===========================
    # Helper Methods
    # ===========================
    
    def _parse_time(self, time_str: str) -> time:
        """Parse HH:MM time string to time object."""
        return datetime.strptime(time_str, '%H:%M').time()
    
    def _time_to_str(self, t: time) -> str:
        """Convert time object to HH:MM string."""
        return t.strftime('%H:%M')

    def _align_time_to_quarter_hour(self, t: time) -> time:
        """Align time to next 15-min boundary (00, 15, 30, 45)."""
        total_minutes = t.hour * 60 + t.minute
        remainder = total_minutes % 15
        if remainder == 0:
            return t
        aligned_minutes = total_minutes + (15 - remainder)
        return self._add_minutes(datetime.min.time(), aligned_minutes)

    def _add_minutes(self, t: time, minutes: int) -> time:
        """Add minutes to a time object."""
        dt = datetime.combine(datetime.today(), t)
        dt += timedelta(minutes=minutes)
        return dt.time()
    
    def _parse_bool(self, value) -> bool:
        """Parse boolean value that might be string or bool."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes')
        return False
    
    def _calculate_sessions_per_week(self, course) -> int:
        """Calculate how many sessions needed per week for a course."""
        # Simple heuristic: credit hours typically map to sessions
        # This can be refined based on course_hours and semester length
        return max(1, course.course_credit)
    
    def _get_suitable_halls(self, course) -> List:
        """Get halls suitable for a course based on type matching."""
        course_type = course.course_type.lower()
        suitable = []
        
        for hall in self.request.halls:
            # Hard constraint: practical -> lab, theory -> lecture
            if course_type == "practical" and hall.hall_type == "lab":
                suitable.append(hall)
            elif course_type == "theory" and hall.hall_type == "lecture":
                suitable.append(hall)
        
        return suitable if suitable else self.request.halls  # Fallback to all
    
    def _is_slot_feasible(self, course, day: str, slot: int, hall) -> bool:
        """Check if a slot is feasible for teacher and hall."""
        # Get slot time range
        if day not in self.slot_times or slot not in self.slot_times[day]:
            return False
        
        slot_start_str, slot_end_str = self.slot_times[day][slot]
        slot_start = self._parse_time(slot_start_str)
        slot_end = self._parse_time(slot_end_str)
        
        # 1. Check teacher busy periods
        for busy_period in self.request.teacher_busy_period:
            if busy_period.teacher_id == course.teacher_id:
                if busy_period.day.lower() == day:
                    busy_start = self._parse_time(busy_period.start_time)
                    busy_end = self._parse_time(busy_period.end_time)
                    # Check if slot overlaps with busy period
                    if self._times_overlap(slot_start, slot_end, busy_start, busy_end):
                        return False
        
        # 2. Check hall busy periods
        for busy_period in self.request.hall_busy_periods:
            if busy_period.hall_id == hall.hall_id:
                # Note: hall_busy_periods don't have day field in schema, 
                # but we check if time overlaps (assuming same day)
                busy_start = self._parse_time(busy_period.start_time)
                busy_end = self._parse_time(busy_period.end_time)
                if self._times_overlap(slot_start, slot_end, busy_start, busy_end):
                    return False
        
        # 3. Check break periods
        if self._is_slot_in_break_period(day, slot_start, slot_end):
            return False
        
        # 4. Check teacher preferred times (if in preference mode)
        if self.respect_preferences:
            if not self._is_slot_in_teacher_preference(course, day, slot_start, slot_end):
                return False
        
        return True
    
    def _times_overlap(self, start1: time, end1: time, start2: time, end2: time) -> bool:
        """Check if two time ranges overlap."""
        # Handle case where time wraps around midnight (end < start)
        if end1 < start1:
            end1 = self._add_minutes(end1, 24 * 60)  # Add 24 hours
        if end2 < start2:
            end2 = self._add_minutes(end2, 24 * 60)
        
        # Check overlap: start1 < end2 and start2 < end1
        return start1 < end2 and start2 < end1
    
    def _get_no_break_days(self) -> List[str]:
        """Days where break is completely removed (no_break_exceptions then daysException)."""
        break_config = self.request.break_period
        top = getattr(break_config, "no_break_exceptions", None)
        if top:
            return [d.lower() for d in top]
        if break_config.constrains:
            return [d.lower() for d in break_config.constrains.daysException]
        return []

    def _get_break_day_override(self, day: str) -> Optional[Tuple[str, str]]:
        """Per-day break (start_time, end_time) if overridden; else None. Apply after no_break."""
        break_config = self.request.break_period
        day = day.lower()
        overrides = getattr(break_config, "day_exceptions", None) or (
            list(break_config.constrains.daysFixedBreaks) if break_config.constrains else []
        )
        if not overrides:
            return None
        for ex in overrides:
            if getattr(ex, "day", ex.get("day") if isinstance(ex, dict) else "").lower() == day:
                s = getattr(ex, "start_time", ex.get("start_time"))
                e = getattr(ex, "end_time", ex.get("end_time"))
                if s and e:
                    return (s, e)
        return None

    def _is_slot_in_break_period(self, day: str, slot_start: time, slot_end: time) -> bool:
        """Check if a slot overlaps with break period. Order: no_break_exceptions, then day_exceptions, else default."""
        break_config = self.request.break_period
        day_lower = day.lower()
        no_break_days = self._get_no_break_days()
        if day_lower in no_break_days:
            return False
        override = self._get_break_day_override(day)
        if override:
            break_start = self._parse_time(override[0])
            break_end = self._parse_time(override[1])
            return self._times_overlap(slot_start, slot_end, break_start, break_end)
        use_daily = self._parse_bool(break_config.daily)
        if use_daily:
            break_start = self._parse_time(break_config.start_time)
            break_end = self._parse_time(break_config.end_time)
            if self._times_overlap(slot_start, slot_end, break_start, break_end):
                return True
        return False
    
    def _is_slot_in_teacher_preference(self, course, day: str, slot_start: time, slot_end: time) -> bool:
        """Check if slot is within teacher's preferred teaching period (strict enforcement)."""
        # If no preferences specified, allow all slots
        if not self.request.teacher_prefered_teaching_period:
            return True
        
        # Check if teacher has any preferences
        teacher_prefs = [
            pref for pref in self.request.teacher_prefered_teaching_period
            if pref.teacher_id == course.teacher_id and pref.day.lower() == day
        ]
        
        # If teacher has preferences for this day, slot MUST be within one of them
        if teacher_prefs:
            for pref in teacher_prefs:
                pref_start = self._parse_time(pref.start_time)
                pref_end = self._parse_time(pref.end_time)
                # Slot must be completely within preferred period
                if slot_start >= pref_start and slot_end <= pref_end:
                    return True
            # Slot is not in any preferred period
            return False
        
        # No preferences for this day, allow the slot
        return True
    
    def _get_break_slots(self, day: str) -> List[ScheduleSlot]:
        """
        Get break time slots for a day. Order: no_break_exceptions (no break), then day_exceptions, else default.
        """
        break_slots = []
        break_config = self.request.break_period
        day_lower = day.lower()
        if day_lower in self._get_no_break_days():
            return []
        override = self._get_break_day_override(day)
        if override:
            break_slots.append(ScheduleSlot(
                day=day.capitalize(),
                start_time=override[0],
                end_time=override[1],
                break_=True
            ))
            return break_slots
        use_daily = self._parse_bool(break_config.daily)
        if use_daily:
            break_slots.append(ScheduleSlot(
                day=day.capitalize(),
                start_time=break_config.start_time,
                end_time=break_config.end_time,
                break_=True
            ))
        return break_slots

    def _parse_max_hours_limit(self, field_value) -> Tuple[Optional[float], Dict[str, float]]:
        """Parse teacher_max_daily_hours or teacher_max_weekly_hours: (default_hours, teacher_exceptions dict)."""
        if field_value is None:
            return None, {}
        if isinstance(field_value, (int, float)):
            return float(field_value), {}
        if isinstance(field_value, dict):
            default = field_value.get("max_hours")
            if default is not None:
                default = float(default)
            exceptions = {}
            for ex in field_value.get("teacher_exceptions", []):
                tid = ex.get("teacher_id")
                mh = ex.get("max_hours")
                if tid is not None and mh is not None:
                    exceptions[tid] = float(mh)
            return default, exceptions
        if isinstance(field_value, str):
            try:
                return float(field_value), {}
            except ValueError:
                return None, {}
        return None, {}

    def _slot_duration_hours(self, start_str: str, end_str: str) -> float:
        """Return duration in hours (fractional) for a slot."""
        start_t = self._parse_time(start_str)
        end_t = self._parse_time(end_str)
        start_dt = datetime.combine(datetime.today(), start_t)
        end_dt = datetime.combine(datetime.today(), end_t)
        if end_dt <= start_dt:
            end_dt += timedelta(days=1)
        return (end_dt - start_dt).total_seconds() / 3600.0

    def _check_soft_constraints(self, timetable: List[DaySchedule]) -> None:
        """Post-solve: check teacher max daily/weekly hours and append to _soft_failures."""
        # Collect teaching slots: (teacher_id, teacher_name, day, start_time, end_time, course_id) -> hours
        teacher_daily: Dict[str, Dict[str, List[Dict]]] = {}  # teacher_id -> day -> list of slot infos
        teacher_weekly: Dict[str, List[Dict]] = {}  # teacher_id -> list of slot infos

        for day_schedule in timetable:
            day = day_schedule.day
            for slot in day_schedule.slots:
                if getattr(slot, "break_", False):
                    continue
                if not getattr(slot, "teacher_id", None):
                    continue
                hours = self._slot_duration_hours(slot.start_time, slot.end_time)
                tid = slot.teacher_id
                info = {
                    "day": day,
                    "start_time": slot.start_time,
                    "end_time": slot.end_time,
                    "course_id": getattr(slot, "course_id", ""),
                    "hours": hours,
                }
                if tid not in teacher_daily:
                    teacher_daily[tid] = {}
                    teacher_weekly[tid] = []
                if day not in teacher_daily[tid]:
                    teacher_daily[tid][day] = []
                teacher_daily[tid][day].append(info)
                teacher_weekly[tid].append(info)

        sc = self.request.soft_constrains
        default_daily, exceptions_daily = self._parse_max_hours_limit(getattr(sc, "teacher_max_daily_hours", None))
        default_weekly, exceptions_weekly = self._parse_max_hours_limit(getattr(sc, "teacher_max_weekly_hours", None))

        # Check daily
        if default_daily is not None:
            daily_blockers = []
            for tid, by_day in teacher_daily.items():
                limit = exceptions_daily.get(tid, default_daily)
                for day, slots in by_day.items():
                    total = sum(s["hours"] for s in slots)
                    if total > limit:
                        teacher_name = (slots[0].get("teacher_name") if slots else "") or next(
                            (t.name for t in self.request.teachers if t.teacher_id == tid), tid
                        )
                        # Resolve teacher name from request if not in slot
                        for t in self.request.teachers:
                            if t.teacher_id == tid:
                                teacher_name = t.name
                                break
                        daily_blockers.append(DiagnosticBlocker(
                            type="TEACHER_MAX_DAILY_HOURS_EXCEEDED",
                            entity={"type": "TEACHER", "id": tid, "name": teacher_name},
                            conflict={"max_allowed_hours": limit, "actual_hours": round(total, 2), "excess": round(total - limit, 2)},
                            evidence={
                                "booked_slots": [
                                    {"day": s["day"], "start_time": s["start_time"], "end_time": s["end_time"], "course_id": s["course_id"], "hours": s["hours"]}
                                    for s in slots
                                ]
                            },
                        ))
            if daily_blockers:
                actuals = [b.conflict.get("actual_hours", 0) for b in daily_blockers if b.conflict]
                suggested = max(actuals, default=default_daily)
                self._soft_failures.append(ConstraintFailure(
                    constraint_failed={"type": "teacher_max_daily_hours", "rule": {"max_daily_hours": default_daily}},
                    blockers=daily_blockers,
                    suggestions=[{"parameter": "teacher_max_daily_hours", "proposed_value": suggested}],
                ))

        # Check weekly
        if default_weekly is not None:
            weekly_blockers = []
            for tid, slots in teacher_weekly.items():
                limit = exceptions_weekly.get(tid, default_weekly)
                total = sum(s["hours"] for s in slots)
                if total > limit:
                    teacher_name = next((t.name for t in self.request.teachers if t.teacher_id == tid), tid)
                    weekly_blockers.append(DiagnosticBlocker(
                        type="TEACHER_MAX_WEEKLY_HOURS_EXCEEDED",
                        entity={"type": "TEACHER", "id": tid, "name": teacher_name},
                        conflict={"max_allowed_hours": limit, "actual_hours": round(total, 2), "excess": round(total - limit, 2)},
                        evidence={
                            "booked_slots": [
                                {"day": s["day"], "start_time": s["start_time"], "end_time": s["end_time"], "course_id": s["course_id"], "hours": s["hours"]}
                                for s in slots
                            ]
                        },
                    ))
            if weekly_blockers:
                self._soft_failures.append(ConstraintFailure(
                    constraint_failed={"type": "teacher_max_weekly_hours", "rule": {"max_weekly_hours": default_weekly}},
                    blockers=weekly_blockers,
                    suggestions=[{"parameter": "teacher_max_weekly_hours", "proposed_value": default_weekly}],
                ))

        # schedule_max_periods_per_day
        max_periods_limit, max_periods_day_exceptions = self._parse_per_day_limit(
            getattr(sc, "schedule_max_periods_per_day", None) or getattr(sc, "time_max_periods_per_day", None)
        )
        if max_periods_limit is not None:
            periods_per_day = {}
            for day_schedule in timetable:
                day = day_schedule.day
                count = sum(1 for s in day_schedule.slots if not getattr(s, "break_", False))
                periods_per_day[day] = count
            for day, count in periods_per_day.items():
                limit = max_periods_day_exceptions.get(day.lower(), max_periods_limit)
                if count > limit:
                    self._soft_failures.append(ConstraintFailure(
                        constraint_failed={"type": "schedule_max_periods_per_day", "details": {"max_periods": max_periods_limit}},
                        blockers=[
                            DiagnosticBlocker(
                                type="MAX_DAILY_PERIODS_EXCEEDED",
                                entity={"type": "daily_periods", "day": day, "max_periods": limit},
                                conflict={"day": day, "current_periods": count},
                                evidence={"daily_schedule": []},
                            )
                        ],
                        suggestions=[{"parameter": "schedule_max_periods_per_day", "proposed_value": count}],
                    ))
                    break

        # schedule_max_free_periods_per_day (gaps in the grid)
        max_free_limit, max_free_day_exceptions = self._parse_per_day_limit(
            getattr(sc, "schedule_max_free_periods_per_day", None) or getattr(sc, "time_min_free_periods_per_day", None)
        )
        if max_free_limit is not None and hasattr(self, "slots_per_day") and self.slots_per_day:
            for day, slot_list in self.slots_per_day.items():
                total_slots = len(slot_list)
                teaching_count = sum(
                    1 for ds in timetable if ds.day.lower() == day.lower()
                    for s in ds.slots if not getattr(s, "break_", False)
                )
                free_count = total_slots - teaching_count
                limit = max_free_day_exceptions.get(day.lower(), max_free_limit)
                if free_count > limit:
                    self._soft_failures.append(ConstraintFailure(
                        constraint_failed={"type": "schedule_max_free_periods_per_day", "details": {"max_free_periods": max_free_limit}},
                        blockers=[
                            DiagnosticBlocker(
                                type="MAX_FREE_PERIODS_EXCEEDED",
                                entity={"type": "daily_free_periods", "day": day},
                                conflict={"day": day, "current_free_periods": free_count, "max_allowed": limit},
                                evidence={},
                            )
                        ],
                        suggestions=[],
                    ))
                    break

        # course_max_daily_frequency
        max_freq_limit, course_exceptions = self._parse_course_frequency_limit(
            getattr(sc, "course_max_daily_frequency", None) or getattr(sc, "time_subject_frequency_per_day", None)
        )
        if max_freq_limit is not None:
            course_daily = {}
            for day_schedule in timetable:
                day = day_schedule.day
                for slot in day_schedule.slots:
                    if getattr(slot, "break_", False):
                        continue
                    cid = getattr(slot, "course_id", None)
                    if not cid:
                        continue
                    key = (day.lower(), cid)
                    course_daily[key] = course_daily.get(key, 0) + 1
            for (day, course_id), count in course_daily.items():
                limit = course_exceptions.get(course_id, max_freq_limit)
                if count > limit:
                    self._soft_failures.append(ConstraintFailure(
                        constraint_failed={"type": "course_max_daily_frequency", "details": {"max_frequency": max_freq_limit}},
                        blockers=[
                            DiagnosticBlocker(
                                type="MAX_COURSE_DAILY_FREQUENCY_EXCEEDED",
                                entity={"type": "COURSE", "id": course_id},
                                conflict={"course_id": course_id, "day": day, "current_frequency": count, "max_allowed": limit},
                                evidence={"course_schedule": []},
                            )
                        ],
                        suggestions=[],
                    ))
                    break

        # Requested placement soft checks (post-solve: compare timetable to requested windows/assignments/free periods)
        self._check_requested_time_windows_and_assignments(timetable)
        self._check_requested_free_periods(timetable)

    def _teaching_slots_from_timetable(self, timetable: List[DaySchedule]) -> List[Dict]:
        """Return list of teaching slot dicts: day, start_time, end_time, teacher_id, hall_id, course_id."""
        out = []
        for day_schedule in timetable:
            day = day_schedule.day
            for slot in day_schedule.slots:
                if getattr(slot, "break_", False):
                    continue
                out.append({
                    "day": day,
                    "start_time": getattr(slot, "start_time", ""),
                    "end_time": getattr(slot, "end_time", ""),
                    "teacher_id": getattr(slot, "teacher_id", ""),
                    "hall_id": getattr(slot, "hall_id", ""),
                    "course_id": getattr(slot, "course_id", ""),
                })
        return out

    def _slot_overlaps_window(self, slot_day: str, slot_start: str, slot_end: str,
                             win_day, win_start: Optional[str], win_end: Optional[str]) -> bool:
        """True if (slot_day, slot_start-slot_end) is within/overlaps window (win_day, win_start-win_end)."""
        slot_day_l = slot_day.lower() if isinstance(slot_day, str) else ""
        win_days = [win_day.lower()] if isinstance(win_day, str) else [d.lower() for d in win_day] if isinstance(win_day, list) else []
        if slot_day_l not in win_days:
            return False
        if not win_start or not win_end:
            return True
        s0 = self._parse_time(slot_start)
        s1 = self._parse_time(slot_end)
        w0 = self._parse_time(win_start)
        w1 = self._parse_time(win_end)
        return self._times_overlap(s0, s1, w0, w1)

    def _expand_requested_days(self, day_spec) -> List[str]:
        """Expand day spec (string or list of days) to list of lowercase day strings."""
        if day_spec is None:
            return []
        if isinstance(day_spec, str):
            return [day_spec.lower()]
        if isinstance(day_spec, list):
            return [d.lower() for d in day_spec if isinstance(d, str)]
        return []

    def _check_requested_time_windows_and_assignments(self, timetable: List[DaySchedule]) -> None:
        """Emit soft failures when course/teacher/hall requested slots or requested_assignments are not satisfied."""
        teaching = self._teaching_slots_from_timetable(timetable)
        sc = self.request.soft_constrains

        # course_requested_time_slots: list of { course_id, slots: [{ day, start_time?, end_time? }] }
        course_requested = getattr(sc, "course_requested_time_slots", None) or []
        if isinstance(course_requested, list):
            for item in course_requested:
                if not isinstance(item, dict):
                    continue
                cid = item.get("course_id")
                if not cid:
                    continue
                slots_spec = item.get("slots") or []
                for t in teaching:
                    if t.get("course_id") != cid:
                        continue
                    matched = False
                    for slot_spec in slots_spec:
                        if not isinstance(slot_spec, dict):
                            continue
                        req_days = self._expand_requested_days(slot_spec.get("day"))
                        if req_days and t["day"].lower() not in req_days:
                            continue
                        req_start = slot_spec.get("start_time")
                        req_end = slot_spec.get("end_time")
                        if req_start and req_end:
                            if self._slot_overlaps_window(t["day"], t["start_time"], t["end_time"], t["day"], req_start, req_end):
                                matched = True
                                break
                        else:
                            matched = True
                            break
                    if not matched:
                        self._soft_failures.append(ConstraintFailure(
                            constraint_failed={"type": "course_requested_time_slots", "details": {"course_id": cid}},
                            blockers=[
                                DiagnosticBlocker(
                                    type="COURSE_SCHEDULED_OUTSIDE_REQUESTED_SLOTS",
                                    entity={"type": "COURSE", "id": cid},
                                    conflict={"day": t["day"], "start_time": t["start_time"], "end_time": t["end_time"]},
                                    evidence={"scheduled_slot": t},
                                )
                            ],
                            suggestions=[],
                        ))
                        break
                break

        # requested_assignments: list of { course_id, teacher_id, hall_id, day?, start_time?, end_time? }
        requested_assignments = getattr(sc, "requested_assignments", None) or []
        if isinstance(requested_assignments, list):
            for req in requested_assignments:
                if not isinstance(req, dict):
                    continue
                cid = req.get("course_id")
                tid = req.get("teacher_id")
                hid = req.get("hall_id")
                rday = req.get("day")
                rstart = req.get("start_time")
                rend = req.get("end_time")
                if not all([cid, tid, hid]):
                    continue
                rday_norm = (rday.lower() if isinstance(rday, str) else (rday[0].lower() if isinstance(rday, list) and rday else "")) if rday else ""
                found = any(
                    t.get("course_id") == cid and t.get("teacher_id") == tid and t.get("hall_id") == hid
                    and (not rday_norm or t["day"].lower() == rday_norm)
                    and (not rstart or not rend or (t["start_time"] == rstart and t["end_time"] == rend))
                    for t in teaching
                )
                if not found:
                    self._soft_failures.append(ConstraintFailure(
                        constraint_failed={"type": "requested_assignments", "details": {"course_id": cid, "teacher_id": tid, "hall_id": hid, "day": rday, "start_time": rstart, "end_time": rend}},
                        blockers=[
                            DiagnosticBlocker(
                                type="REQUESTED_ASSIGNMENT_NOT_SATISFIED",
                                entity={"type": "COURSE", "id": cid},
                                conflict={"requested": req},
                                evidence={},
                            )
                        ],
                        suggestions=[],
                    ))

        # teacher_requested_time_windows: list of { teacher_id, windows: [{ day, start_time?, end_time? }] }
        teacher_windows = getattr(sc, "teacher_requested_time_windows", None) or []
        if isinstance(teacher_windows, list):
            for tw in teacher_windows:
                if not isinstance(tw, dict):
                    continue
                teacher_id = tw.get("teacher_id")
                windows = tw.get("windows") or []
                for t in teaching:
                    if t.get("teacher_id") != teacher_id:
                        continue
                    matched = any(
                        self._slot_overlaps_window(
                            t["day"], t["start_time"], t["end_time"],
                            w.get("day"), w.get("start_time"), w.get("end_time")
                        )
                        for w in windows if isinstance(w, dict)
                    )
                    if not matched:
                        self._soft_failures.append(ConstraintFailure(
                            constraint_failed={"type": "teacher_requested_time_windows", "details": {"teacher_id": teacher_id}},
                            blockers=[
                                DiagnosticBlocker(
                                    type="TEACHER_SCHEDULED_OUTSIDE_REQUESTED_WINDOWS",
                                    entity={"type": "TEACHER", "id": teacher_id},
                                    conflict={"day": t["day"], "start_time": t["start_time"], "end_time": t["end_time"]},
                                    evidence={"scheduled_slot": t},
                                )
                            ],
                            suggestions=[],
                        ))
                        break
                break

        # hall_requested_time_windows: list of { hall_id, windows: [{ day, start_time?, end_time? }] }
        hall_windows = getattr(sc, "hall_requested_time_windows", None) or []
        if isinstance(hall_windows, list):
            for hw in hall_windows:
                if not isinstance(hw, dict):
                    continue
                hall_id = hw.get("hall_id")
                windows = hw.get("windows") or []
                for t in teaching:
                    if t.get("hall_id") != hall_id:
                        continue
                    matched = any(
                        self._slot_overlaps_window(
                            t["day"], t["start_time"], t["end_time"],
                            w.get("day"), w.get("start_time"), w.get("end_time")
                        )
                        for w in windows if isinstance(w, dict)
                    )
                    if not matched:
                        self._soft_failures.append(ConstraintFailure(
                            constraint_failed={"type": "hall_requested_time_windows", "details": {"hall_id": hall_id}},
                            blockers=[
                                DiagnosticBlocker(
                                    type="HALL_SCHEDULED_OUTSIDE_REQUESTED_WINDOWS",
                                    entity={"type": "HALL", "id": hall_id},
                                    conflict={"day": t["day"], "start_time": t["start_time"], "end_time": t["end_time"]},
                                    evidence={"scheduled_slot": t},
                                )
                            ],
                            suggestions=[],
                        ))
                        break
                break

    def _check_requested_free_periods(self, timetable: List[DaySchedule]) -> None:
        """Emit soft failure when a requested free period is occupied by a class."""
        teaching = self._teaching_slots_from_timetable(timetable)
        requested = getattr(self.request.soft_constrains, "requested_free_periods", None) or []
        if not isinstance(requested, list):
            return
        for req in requested:
            if not isinstance(req, dict):
                continue
            req_days = self._expand_requested_days(req.get("day"))
            req_start = req.get("start_time")
            req_end = req.get("end_time")
            if not req_days:
                continue
            if not req_start or not req_end:
                continue
            for t in teaching:
                if t["day"].lower() not in req_days:
                    continue
                if self._slot_overlaps_window(t["day"], t["start_time"], t["end_time"], t["day"], req_start, req_end):
                    self._soft_failures.append(ConstraintFailure(
                        constraint_failed={"type": "requested_free_period", "details": {"day": req.get("day"), "start_time": req_start, "end_time": req_end}},
                        blockers=[
                            DiagnosticBlocker(
                                type="REQUESTED_FREE_PERIOD_OCCUPIED",
                                entity={"type": "TIME_SLOT", "day": t["day"], "start_time": t["start_time"], "end_time": t["end_time"]},
                                conflict={"requested_free": req, "scheduled_course": t.get("course_id")},
                                evidence={"scheduled_slot": t},
                            )
                        ],
                        suggestions=[],
                    ))
                    break

    def _parse_per_day_limit(self, field_value) -> Tuple[Optional[int], Dict[str, int]]:
        """Parse max_periods or max_free_periods: (default_limit, day_exceptions dict)."""
        if field_value is None:
            return None, {}
        if isinstance(field_value, (int, float)):
            return int(field_value), {}
        if isinstance(field_value, dict):
            default = field_value.get("max_periods") or field_value.get("max_free_periods")
            if default is not None:
                default = int(default)
            exceptions = {}
            for ex in field_value.get("day_exceptions", []):
                d = ex.get("day", "").lower()
                v = ex.get("max_periods") or ex.get("max_free_periods")
                if d and v is not None:
                    exceptions[d] = int(v)
            return default, exceptions
        if isinstance(field_value, str):
            try:
                return int(field_value), {}
            except ValueError:
                return None, {}
        return None, {}

    def _parse_course_frequency_limit(self, field_value) -> Tuple[Optional[int], Dict[str, int]]:
        """Parse course_max_daily_frequency: (default_max_frequency, course_exceptions dict)."""
        if field_value is None:
            return None, {}
        if isinstance(field_value, (int, float)):
            return int(field_value), {}
        if isinstance(field_value, dict):
            default = field_value.get("max_frequency")
            if default is not None:
                default = int(default)
            exceptions = {}
            for ex in field_value.get("course_exceptions", []):
                cid = ex.get("course_id")
                v = ex.get("max_frequency")
                if cid is not None and v is not None:
                    exceptions[cid] = int(v)
            return default, exceptions
        if isinstance(field_value, str):
            try:
                return int(field_value), {}
            except ValueError:
                return None, {}
        return None, {}

    def _build_response(
        self,
        status: str,
        timetable: List[DaySchedule],
        solve_time: float,
        hard_failures: Optional[List[ConstraintFailure]] = None,
        soft_failures: Optional[List[ConstraintFailure]] = None,
    ) -> SchedulingResponse:
        """Build response with diagnostics and summary (RC-01 to RC-04, DR-01)."""
        hard_failures = hard_failures if hard_failures is not None else self._hard_failures
        soft_failures = soft_failures if soft_failures is not None else self._soft_failures
        hard_met = len(hard_failures) == 0
        soft_met = len(soft_failures) == 0

        if status not in ("OPTIMAL", "PARTIAL", "ERROR"):
            status = "ERROR" if not hard_met else ("PARTIAL" if not soft_met else "OPTIMAL")

        if hard_met and soft_met:
            summary_msg = "All constraints satisfied."
        elif hard_met and not soft_met:
            summary_msg = "Timetable generated, but some preferences could not be met."
        else:
            summary_msg = "Unable to generate a valid timetable."

        diagnostics = Diagnostics(
            constraints=DiagnosticsConstraints(hard=hard_failures, soft=soft_failures),
            summary=DiagnosticsSummary(
                message=summary_msg,
                hard_constraints_met=hard_met,
                soft_constraints_met=soft_met,
                failed_soft_constraints_count=len(soft_failures),
                failed_hard_constraints_count=len(hard_failures),
            ),
        )
        legacy_messages = Messages(error_message=self.errors)
        return SchedulingResponse(
            status=status,
            timetable=timetable,
            diagnostics=diagnostics,
            metadata=ResponseMetadata(solve_time_seconds=solve_time),
            messages=legacy_messages,
            solve_time_seconds=solve_time,
        )

    def _create_infeasible_response(self, errors: List[str]) -> SchedulingResponse:
        """Create response for infeasible problem (ERROR status, hard diagnostic)."""
        blockers = [
            DiagnosticBlocker(
                type="INFEASIBLE_SCHEDULE",
                conflict={"reason": err},
                evidence={"validation_errors": errors},
            )
            for err in errors
        ]
        if not blockers:
            blockers = [
                DiagnosticBlocker(
                    type="INFEASIBLE_SCHEDULE",
                    conflict={"reason": "No feasible schedule exists."},
                    evidence={},
                )
            ]
        failure = ConstraintFailure(
            constraint_failed={"type": "INFEASIBLE_SCHEDULE", "details": {"errors": errors}},
            blockers=blockers,
            suggestions=[
                {"action": "RELAX_CONSTRAINTS", "message": "Try relaxing constraints, adding more halls or time slots, or reducing course hours."}
            ],
        )
        self._hard_failures = [failure]
        for err in errors:
            self.errors.append(
                ErrorMessage(
                    constraint_type="HARD",
                    severity="ERROR",
                    code="INFEASIBLE_SCHEDULE",
                    title="Infeasible Schedule",
                    description=err,
                    root_causes=[RootCause(cause="Constraint conflict", details="The provided constraints cannot be satisfied simultaneously.")],
                    resolution_hint="Try relaxing constraints, adding more halls or time slots, or reducing course hours.",
                )
            )
        return self._build_response("ERROR", [], 0.0, hard_failures=[failure], soft_failures=[])

    def _create_error_response(self, error: str) -> SchedulingResponse:
        """Create response for solver error (ERROR status, hard diagnostic)."""
        failure = ConstraintFailure(
            constraint_failed={"type": "SOLVER_ERROR", "details": {"message": error}},
            blockers=[
                DiagnosticBlocker(
                    type="SOLVER_ERROR",
                    conflict={"message": error},
                    evidence={},
                )
            ],
            suggestions=[
                {"action": "RETRY_OR_CONTACT_SUPPORT", "message": "Please check your input data and try again. If the problem persists, contact support."}
            ],
        )
        self._hard_failures = [failure]
        self.errors.append(
            ErrorMessage(
                constraint_type="HARD",
                severity="ERROR",
                code="SOLVER_ERROR",
                title="Solver Error",
                description=error,
                root_causes=[RootCause(cause="Unexpected solver failure", details=error)],
                resolution_hint="Please check your input data and try again. If the problem persists, contact support.",
            )
        )
        return self._build_response("ERROR", [], 0.0, hard_failures=[failure], soft_failures=[])
    
    def _build_teacher_course_map(self) -> Dict[str, List[int]]:
        """Build mapping from teacher_id to list of course indices."""
        teacher_courses = {}
        for idx, course in enumerate(self.request.teacher_courses):
            teacher_id = course.teacher_id
            if teacher_id not in teacher_courses:
                teacher_courses[teacher_id] = []
            teacher_courses[teacher_id].append(idx)
        return teacher_courses
    
    def _format_duration(self, start_str: str, end_str: str) -> str:
        """Format duration between two times as 'Xh Ymin'."""
        start = self._parse_time(start_str)
        end = self._parse_time(end_str)
        
        start_dt = datetime.combine(datetime.today(), start)
        end_dt = datetime.combine(datetime.today(), end)
        
        duration = end_dt - start_dt
        total_minutes = int(duration.total_seconds() / 60)
        
        hours = total_minutes // 60
        minutes = total_minutes % 60
        
        if hours > 0 and minutes > 0:
            return f"{hours}h {minutes}min"
        elif hours > 0:
            return f"{hours}h"
        else:
            return f"{minutes}min"
