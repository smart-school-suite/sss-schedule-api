import random
from datetime import datetime, timedelta
from typing import List, Dict
from models.schemas import SchedulingRequest, SchedulingResponse, ScheduleItem
from itertools import product

class Scheduler:
    def __init__(self, request: SchedulingRequest):
        self.request = request
        self.days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        self.schedule = []
        self.time_slots = self._generate_time_slots()

    def _parse_time(self, time_str: str) -> datetime:
        """Parse ISO 8601 or HH:MM time string to datetime."""
        try:
            # Try parsing ISO 8601 format
            return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        except ValueError:
            # Try parsing HH:MM format
            return datetime.strptime(time_str, '%H:%M')

    def _generate_time_slots(self) -> List[datetime]:
        """Generate available time slots based on school hours and lesson slot length."""
        start_time = self._parse_time(self.request.constraints['school_start_time'])
        end_time = self._parse_time(self.request.constraints['school_end_time'])
        slot_length = timedelta(minutes=self.request.constraints['lesson_slot_length'])
        lunch_start = self._parse_time(self.request.constraints['lunch_break_start_time'])
        lunch_end = self._parse_time(self.request.constraints['lunch_break_end_time'])

        slots = []
        current_time = start_time
        while current_time + slot_length <= end_time:
            # Skip lunch break
            if not (self.request.constraints['lunch_break'] and
                    lunch_start <= current_time < lunch_end):
                slots.append(current_time)
            current_time += slot_length
        return slots

    def _is_teacher_available(self, teacher_id: str, day: str, start_time: datetime, duration: int) -> bool:
        """Check if a teacher is available for a given time slot."""
        end_time = start_time + timedelta(minutes=duration)

        # Check teacher busy times
        for busy_time in self.request.teacher_busy_times:
            if busy_time.teacher_id == teacher_id and busy_time.day_of_week == day:
                busy_start = self._parse_time(busy_time.start_time)
                busy_end = self._parse_time(busy_time.end_time)
                if busy_start <= start_time < busy_end or busy_start < end_time <= busy_end:
                    return False

        # Check teacher availability (if specified)
        if self.request.teacher_available_times:
            for avail in self.request.teacher_available_times:
                if avail.teacher_id == teacher_id:
                    avail_start = self._parse_time(avail.start_time)
                    avail_end = self._parse_time(avail.end_time)
                    if avail_start <= start_time and end_time <= avail_end:
                        return True
            return False
        return True

    def _is_hall_available(self, hall_id: str, day: str, start_time: datetime, duration: int) -> bool:
        """Check if a hall is available for a given time slot."""
        end_time = start_time + timedelta(minutes=duration)
        for busy_time in self.request.hall_busy_times:
            if busy_time.hall_id == hall_id and busy_time.day_of_week == day:
                busy_start = self._parse_time(busy_time.start_time)
                busy_end = self._parse_time(busy_time.end_time)
                if busy_start <= start_time < busy_end or busy_start < end_time <= busy_end:
                    return False
        return True

    def _check_constraints(self, schedule: List[ScheduleItem]) -> bool:
        """Validate the schedule against all constraints."""
        teacher_loads = {t.teacher_id: 0 for t in self.request.teachers}
        daily_counts = {t.teacher_id: {day: 0 for day in self.days} for t in self.request.teachers}
        weekly_counts = {t.teacher_id: 0 for t in self.request.teachers}

        for item in schedule:
            teacher_loads[item.teacher_id] += int(item.duration)
            daily_counts[item.teacher_id][item.day_of_week] += 1
            weekly_counts[item.teacher_id] += 1

        for teacher_id in teacher_loads:
            if not (self.request.constraints['min_weekly_load'] <= teacher_loads[teacher_id] <= self.request.constraints['max_weekly_load']):
                return False
            if not (self.request.constraints['min_weekly_course_frequency'] <= weekly_counts[teacher_id] <= self.request.constraints['max_weekly_course_frequency']):
                return False
            for day in self.days:
                if not (self.request.constraints['min_courses_per_day'] <= daily_counts[teacher_id][day] <= self.request.constraints['max_courses_per_day']):
                    return False
        return True

    def generate_schedule(self) -> SchedulingResponse:
        """Generate a schedule based on the constraints and availability."""
        self.schedule = []
        course_counts = {course.id: 0 for course in self.request.teacher_courses}
        max_attempts = 1000
        attempt = 0

        # Shuffle courses to ensure randomness
        courses = self.request.teacher_courses.copy()
        random.shuffle(courses)

        while courses and attempt < max_attempts:
            for course in courses[:]:
                teacher = next(t for t in self.request.teachers if t.teacher_id == course.teacher_id)
                hall = random.choice(self.request.halls) if self.request.halls else None
                day = random.choice(self.days)
                start_time = random.choice(self.time_slots)
                duration = self.request.constraints['course_duration']

                if (self._is_teacher_available(teacher.teacher_id, day, start_time, duration) and
                    (not hall or self._is_hall_available(hall.hall_id, day, start_time, duration)) and
                    course_counts[course.id] < self.request.constraints['max_weekly_course_frequency']):

                    # Check for conflicts with existing schedule
                    conflict = False
                    for item in self.schedule:
                        if (item.day_of_week == day and
                            item.start_time == start_time.strftime('%H:%M') and
                            (item.teacher_id == teacher.teacher_id or item.hall_id == hall.hall_id)):
                            conflict = True
                            break

                    if not conflict:
                        schedule_item = ScheduleItem(
                            id=str(len(self.schedule) + 1),
                            teacher_id=teacher.teacher_id,
                            teacher_name=teacher.name,
                            start_time=start_time.strftime('%H:%M'),
                            end_time=(start_time + timedelta(minutes=duration)).strftime('%H:%M'),
                            day_of_week=day,
                            duration=str(duration),
                            course_id=course.course_id,
                            course_title=course.course_title,
                            course_code=course.course_code,
                            hall_id=hall.hall_id if hall else '',
                            hall_name=hall.name if hall else ''
                        )
                        self.schedule.append(schedule_item)
                        course_counts[course.id] += 1
                        if course_counts[course.id] >= self.request.constraints['min_weekly_course_frequency']:
                            courses.remove(course)

            attempt += 1

        is_optimal = self._check_constraints(self.schedule)
        solution_info = "Schedule generated successfully" if is_optimal else "Suboptimal schedule due to constraint violations or max attempts reached"

        return SchedulingResponse(
            schedule=self.schedule,
            is_optimal=is_optimal,
            solution_info=solution_info
        )