from fastapi import APIRouter
from models.schemas import SchedulingRequest, SchedulingResponse
from service.ortools_solver import ORToolsScheduler

# Create a router instance
router = APIRouter()


@router.post("/schedule/with-preference", response_model=SchedulingResponse)
async def solve_schedule_with_preference(request: SchedulingRequest):
    """
    Generate timetable considering teacher preferred teaching times.
    
    This endpoint respects soft constraints for teacher preferences,
    attempting to schedule courses during their preferred time slots.
    """
    scheduler = ORToolsScheduler(respect_preferences=True, time_limit_seconds=30)
    response = scheduler.solve_scheduling(request)
    return response


@router.post("/schedule/without-preference", response_model=SchedulingResponse)
async def solve_schedule_without_preference(request: SchedulingRequest):
    """
    Generate timetable ignoring teacher preferred teaching times.
    
    This endpoint focuses solely on feasibility and structural constraints,
    without considering teacher time preferences.
    """
    scheduler = ORToolsScheduler(respect_preferences=False, time_limit_seconds=30)
    response = scheduler.solve_scheduling(request)
    return response
