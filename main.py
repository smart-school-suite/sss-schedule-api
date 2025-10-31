import uvicorn
from fastapi import FastAPI
from routers import schedule

# Initialize the FastAPI application
app = FastAPI(
    title="OR-Tools Scheduling API",
    description="A simple API to solve scheduling problems using Google OR-Tools."
)

# Include the schedule router
app.include_router(schedule.router, prefix="/api", tags=["scheduling"])

@app.get("/")
async def read_root():
    return {"message": "Welcome to the OR-Tools Scheduling API. Visit /docs to see the available endpoints."}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
