"""
OR-Tools CP-SAT based scheduling solver.

This module implements a comprehensive constraint satisfaction and optimization
solver for school timetabling using Google OR-Tools CP-SAT solver.
"""

from ortools.sat.python import cp_model
from typing import List, Dict, Tuple, Optional, Set
from models.schemas import (
    SchedulingRequest, SchedulingResponse, DaySchedule, ScheduleSlot,
    Messages, ErrorMessage, AffectedEntity, RootCause
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
        """Build discrete time slots for each day with configurable duration."""
        for day in self.days:
            # Get period duration for this day
            period_duration = self._get_period_duration(day)
            
            start_str, end_str = self.operational_hours[day]
            start_time = self._parse_time(start_str)
            end_time = self._parse_time(end_str)
            
            # Generate slots
            slots = []
            slot_times = {}
            current_time = start_time
            slot_idx = 0
            
            while current_time < end_time:
                next_time = self._add_minutes(current_time, period_duration)
                if next_time > end_time:
                    next_time = end_time
                
                slots.append(slot_idx)
                slot_times[slot_idx] = (
                    self._time_to_str(current_time),
                    self._time_to_str(next_time)
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
        
        # Validate days_exception
        if break_config.constrains:
            valid_days = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
            for day in break_config.constrains.daysException:
                if day.lower() not in valid_days:
                    errors.append(f"Invalid day '{day}' in days_exception. Use valid weekdays: Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, or Sunday")
            
            # Validate days_fixed_breaks
            for fixed_break in break_config.constrains.daysFixedBreaks:
                if fixed_break.day.lower() not in valid_days:
                    errors.append(f"Invalid day '{fixed_break.day}' in days_fixed_breaks. Use valid weekdays")
                
                try:
                    fb_start = self._parse_time(fixed_break.start_time)
                    fb_end = self._parse_time(fixed_break.end_time)
                    if fb_start >= fb_end:
                        errors.append(f"Fixed break for {fixed_break.day}: start time ({fixed_break.start_time}) must be before end time ({fixed_break.end_time})")
                except ValueError:
                    errors.append(f"Invalid time format in fixed break for {fixed_break.day}. Use HH:MM format")
        
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
        
        status_str = "OPTIMAL" if status == cp_model.OPTIMAL else "FEASIBLE"
        
        return SchedulingResponse(
            timetable=timetable,
            messages=Messages(error_message=[]),
            status=status_str,
            solve_time_seconds=solve_time
        )
    
    # ===========================
    # Helper Methods
    # ===========================
    
    def _parse_time(self, time_str: str) -> time:
        """Parse HH:MM time string to time object."""
        return datetime.strptime(time_str, '%H:%M').time()
    
    def _time_to_str(self, t: time) -> str:
        """Convert time object to HH:MM string."""
        return t.strftime('%H:%M')
    
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
    
    def _is_slot_in_break_period(self, day: str, slot_start: time, slot_end: time) -> bool:
        """Check if a slot overlaps with break period for the given day."""
        break_config = self.request.break_period
        
        # Check if day is in exceptions - no break on exception days
        if break_config.constrains:
            if day in [d.lower() for d in break_config.constrains.daysException]:
                return False  # No break on exception days, so slot is not in break
        
        # Check for fixed break on this day
        if break_config.constrains and break_config.constrains.daysFixedBreaks:
            for fixed_break in break_config.constrains.daysFixedBreaks:
                if fixed_break.day.lower() == day:
                    break_start = self._parse_time(fixed_break.start_time)
                    break_end = self._parse_time(fixed_break.end_time)
                    if self._times_overlap(slot_start, slot_end, break_start, break_end):
                        return True
                    return False  # Fixed break exists but doesn't overlap
        
        # Use default break if daily is true
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
        Get break time slots for a day.
        
        Logic:
        1. If day is in days_exception, return empty (no break)
        2. If day has a fixed break in days_fixed_breaks, use that
        3. If daily is true and no fixed break, use default break times
        4. Otherwise, no break
        """
        break_slots = []
        break_config = self.request.break_period
        
        # Step 1: Check if day is in exceptions - skip break entirely
        if break_config.constrains:
            if day in [d.lower() for d in break_config.constrains.daysException]:
                return []  # No break on exception days
        
        # Step 2: Check for fixed break on this specific day
        if break_config.constrains and break_config.constrains.daysFixedBreaks:
            for fixed_break in break_config.constrains.daysFixedBreaks:
                if fixed_break.day.lower() == day:
                    # Use the fixed break time for this day
                    break_slots.append(ScheduleSlot(
                        day=day.capitalize(),
                        start_time=fixed_break.start_time,
                        end_time=fixed_break.end_time,
                        break_=True
                    ))
                    return break_slots  # Fixed break overrides default
        
        # Step 3: Use default break if daily is true
        use_daily = self._parse_bool(break_config.daily)
        if use_daily:
            break_slots.append(ScheduleSlot(
                day=day.capitalize(),
                start_time=break_config.start_time,
                end_time=break_config.end_time,
                break_=True
            ))
        
        return break_slots
    
    def _create_infeasible_response(self, errors: List[str]) -> SchedulingResponse:
        """Create response for infeasible problem."""
        error_messages = []
        
        for err in errors:
            # Create detailed error message
            error_msg = ErrorMessage(
                constraint_type="HARD",
                severity="ERROR",
                code="INFEASIBLE_SCHEDULE",
                title="Infeasible Schedule",
                description=err,
                root_causes=[
                    RootCause(
                        cause="Constraint conflict",
                        details="The provided constraints cannot be satisfied simultaneously."
                    )
                ],
                resolution_hint="Try relaxing constraints, adding more halls or time slots, or reducing course hours."
            )
            error_messages.append(error_msg)
        
        return SchedulingResponse(
            timetable=[],
            messages=Messages(error_message=error_messages),
            status="INFEASIBLE",
            solve_time_seconds=0.0
        )
    
    def _create_error_response(self, error: str) -> SchedulingResponse:
        """Create response for solver error."""
        return SchedulingResponse(
            timetable=[],
            messages=Messages(error_message=[
                ErrorMessage(
                    constraint_type="HARD",
                    severity="ERROR",
                    code="SOLVER_ERROR",
                    title="Solver Error",
                    description=error,
                    root_causes=[
                        RootCause(
                            cause="Unexpected solver failure",
                            details=error
                        )
                    ],
                    resolution_hint="Please check your input data and try again. If the problem persists, contact support."
                )
            ]),
            status="ERROR",
            solve_time_seconds=0.0
        )
    
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
