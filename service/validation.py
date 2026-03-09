"""
Pre-scheduling validation for soft constraint and preference inputs.
Rejects partial or invalid entries so the API returns 422 before the solver runs.
"""
from typing import List, Tuple, Any, Dict, Optional


def _get(lst: Any, default: list) -> list:
    if lst is None:
        return default
    return lst if isinstance(lst, list) else default


def _has(d: Dict, *keys: str) -> bool:
    return all(d.get(k) is not None and d.get(k) != "" for k in keys)


def validate_soft_constraints_inputs(soft_constrains: Any) -> List[Tuple[str, str]]:
    """
    Validate soft constraint shapes. Returns list of (field_path, message).
    Call before scheduling; if non-empty, return 422.
    """
    errors: List[Tuple[str, str]] = []
    if soft_constrains is None:
        return errors

    # requested_free_periods: reject partial time (only start_time, or only end_time, or day+one time)
    requested_free = _get(getattr(soft_constrains, "requested_free_periods", None), [])
    for i, entry in enumerate(requested_free):
        if not isinstance(entry, dict):
            continue
        path = f"soft_constrains.requested_free_periods[{i}]"
        has_start = "start_time" in entry and entry.get("start_time") not in (None, "")
        has_end = "end_time" in entry and entry.get("end_time") not in (None, "")
        has_day = "day" in entry and entry.get("day") not in (None, "")
        if has_start and not has_end:
            errors.append((path, "start_time requires end_time"))
        elif has_end and not has_start:
            errors.append((path, "end_time requires start_time"))
        elif has_day and (has_start != has_end):
            errors.append((path, "when day is provided, both start_time and end_time are required"))

    # teacher_requested_time_windows: each window must have day + start_time + end_time
    teacher_windows = _get(getattr(soft_constrains, "teacher_requested_time_windows", None), [])
    for i, tw in enumerate(teacher_windows):
        if not isinstance(tw, dict):
            continue
        windows = _get(tw.get("windows") or tw.get("requested_time_windows"), [])
        for j, w in enumerate(windows):
            if not isinstance(w, dict):
                continue
            path = f"soft_constrains.teacher_requested_time_windows[{i}].windows[{j}]"
            if not _has(w, "day", "start_time", "end_time"):
                errors.append((path, "each window must have day, start_time, and end_time"))

    # hall_requested_time_windows: same
    hall_windows = _get(getattr(soft_constrains, "hall_requested_time_windows", None), [])
    for i, hw in enumerate(hall_windows):
        if not isinstance(hw, dict):
            continue
        windows = _get(hw.get("windows") or hw.get("requested_time_windows"), [])
        for j, w in enumerate(windows):
            if not isinstance(w, dict):
                continue
            path = f"soft_constrains.hall_requested_time_windows[{i}].windows[{j}]"
            if not _has(w, "day", "start_time", "end_time"):
                errors.append((path, "each window must have day, start_time, and end_time"))

    # requested_assignments: course_id, teacher_id, hall_id required; placement = day + start_time + end_time
    requested_assignments = _get(getattr(soft_constrains, "requested_assignments", None), [])
    for i, req in enumerate(requested_assignments):
        if not isinstance(req, dict):
            continue
        path = f"soft_constrains.requested_assignments[{i}]"
        if not _has(req, "course_id", "teacher_id", "hall_id"):
            missing = [k for k in ("course_id", "teacher_id", "hall_id") if not _has(req, k)]
            errors.append((path, f"required: {', '.join(missing)}"))
        has_day = "day" in req and req.get("day") not in (None, "")
        has_start = "start_time" in req and req.get("start_time") not in (None, "")
        has_end = "end_time" in req and req.get("end_time") not in (None, "")
        if has_start and not has_end:
            errors.append((path, "start_time requires end_time"))
        elif has_end and not has_start:
            errors.append((path, "end_time requires start_time"))
        elif has_day and (has_start != has_end):
            errors.append((path, "when day is provided, both start_time and end_time are required"))

    # course_requested_time_slots: each slot must have day + start_time + end_time
    course_slots = _get(getattr(soft_constrains, "course_requested_time_slots", None), [])
    for i, item in enumerate(course_slots):
        if not isinstance(item, dict):
            continue
        slots = _get(item.get("slots") or item.get("requested_time_slots"), [])
        for j, slot in enumerate(slots):
            if not isinstance(slot, dict):
                continue
            path = f"soft_constrains.course_requested_time_slots[{i}].slots[{j}]"
            if not _has(slot, "day", "start_time", "end_time"):
                errors.append((path, "each slot must have day, start_time, and end_time"))

    return errors


def validate_teacher_preference_required(teacher_prefered_teaching_period: Any) -> List[Tuple[str, str]]:
    """
    For the with-preference endpoint: teacher preference data must be present and non-empty.
    Returns list of (field_path, message).
    """
    errors: List[Tuple[str, str]] = []
    if teacher_prefered_teaching_period is None:
        errors.append(("teacher_prefered_teaching_period", "required when scheduling with preferences"))
    elif not isinstance(teacher_prefered_teaching_period, list) or len(teacher_prefered_teaching_period) == 0:
        errors.append(("teacher_prefered_teaching_period", "must be a non-empty array when using with-preference endpoint"))
    return errors
