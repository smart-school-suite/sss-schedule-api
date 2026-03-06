from typing import Any, Dict, Union

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from models.schemas import (
    BackendScheduleRequest,
    SchedulingRequest,
    SchedulingResponse,
    backend_request_to_scheduling_request,
)
from service.ortools_solver import ORToolsScheduler

# Create a router instance
router = APIRouter()


def _validation_errors_detail(ve: ValidationError) -> Dict[str, list]:
    """Build {field_path: [msg, ...]} for 422 response."""
    out: Dict[str, list] = {}
    for err in ve.errors():
        key = ".".join(str(x) for x in err.get("loc", []))
        msg = err.get("msg", "")
        out.setdefault(key, []).append(msg)
    return out


def _normalize_to_internal(payload: Union[BackendScheduleRequest, SchedulingRequest, Dict[str, Any]]) -> SchedulingRequest:
    """
    Accept either backend format (hard_constraints, teacher_preferred_periods, etc.)
    or legacy format (break_period/operational_period at top level). Return SchedulingRequest.
    """
    if isinstance(payload, SchedulingRequest):
        return payload
    if isinstance(payload, BackendScheduleRequest):
        return backend_request_to_scheduling_request(payload)
    # Raw dict: detect format and parse
    if isinstance(payload, dict) and "hard_constraints" in payload:
        return backend_request_to_scheduling_request(BackendScheduleRequest(**payload))
    return SchedulingRequest(**payload)


@router.post("/schedule/with-preference", response_model=SchedulingResponse)
async def solve_schedule_with_preference(
    body: Dict[str, Any] = Body(..., description="Backend format or legacy SchedulingRequest"),
):
    """
    Generate timetable considering teacher preferred teaching times.
    Accepts backend format (hard_constraints, teachers[].teacher_name, etc.) or legacy format.
    """
    try:
        if "hard_constraints" in body:
            request = BackendScheduleRequest(**body)
        else:
            request = SchedulingRequest(**body)
    except ValidationError as e:
        return JSONResponse(status_code=422, content={"errors": _validation_errors_detail(e)})
    internal = _normalize_to_internal(request)
    scheduler = ORToolsScheduler(respect_preferences=True, time_limit_seconds=30)
    return scheduler.solve_scheduling(internal)


@router.post("/schedule/without-preference", response_model=SchedulingResponse)
async def solve_schedule_without_preference(
    body: Dict[str, Any] = Body(..., description="Backend format or legacy SchedulingRequest"),
):
    """
    Generate timetable ignoring teacher preferred teaching times.
    Same request body format as with-preference.
    """
    try:
        if "hard_constraints" in body:
            request = BackendScheduleRequest(**body)
        else:
            request = SchedulingRequest(**body)
    except ValidationError as e:
        return JSONResponse(status_code=422, content={"errors": _validation_errors_detail(e)})
    internal = _normalize_to_internal(request)
    scheduler = ORToolsScheduler(respect_preferences=False, time_limit_seconds=30)
    return scheduler.solve_scheduling(internal)
