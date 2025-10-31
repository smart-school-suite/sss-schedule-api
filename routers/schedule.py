from fastapi import APIRouter
from models.schemas import SchedulingRequest, SchedulingResponse
from service.scheduler import ORToolsScheduler

# Create a router instance
router = APIRouter()

@router.post("/schedule", response_model=SchedulingResponse)
async def solve_schedule(request: SchedulingRequest):
    """
    Endpoint to solve a scheduling problem.
    """
    scheduler = ORToolsScheduler()
    response = scheduler.solve_scheduling(request)
    return response
