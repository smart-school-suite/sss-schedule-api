"""
Main FastAPI application entry point.
"""
import uvicorn
import logging
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from routers import schedule
from config import settings

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize the FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A comprehensive API to solve school scheduling problems using Google OR-Tools CP-SAT solver.",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Convert FastAPI validation errors to human-friendly format.
    
    Expected format:
    {
        "errors": {
            "field_name": ["Error message 1", "Error message 2"]
        }
    }
    """
    errors = {}
    
    for error in exc.errors():
        # Extract field name from error location
        field_path = error.get("loc", [])
        
        # Skip "body" prefix and build field name
        if len(field_path) > 1 and field_path[0] == "body":
            field_path = field_path[1:]
        
        # Convert field path to human-readable name
        field_name = " -> ".join(str(p) for p in field_path)
        
        # Convert snake_case to Title Case with spaces
        field_name = field_name.replace("_", " ").title()
        
        # Handle special cases for better readability
        field_name = field_name.replace("Teacher Prefered Teaching Period", "Preferred Teaching Period")
        field_name = field_name.replace("Teacher Busy Period", "Teacher Busy Period")
        field_name = field_name.replace("Hall Busy Periods", "Hall Busy Periods")
        field_name = field_name.replace("Break Period", "Break Period")
        field_name = field_name.replace("Operational Period", "Operational Period")
        field_name = field_name.replace("Soft Constrains", "Soft Constraints")
        
        # Get error message
        error_msg = error.get("msg", "Invalid value")
        error_type = error.get("type", "")
        
        # Create human-friendly messages
        if error_type == "missing":
            error_msg = f"{field_name} is required."
        elif error_type == "value_error.missing":
            error_msg = f"{field_name} is required."
        elif error_type == "type_error":
            error_msg = f"{field_name} has an invalid type. {error_msg}"
        elif "uuid" in error_type.lower():
            error_msg = f"{field_name} must be a valid UUID format."
        elif "time" in error_type.lower() or "datetime" in error_type.lower():
            error_msg = f"{field_name} must be in HH:MM format (e.g., '12:00')."
        elif "greater_than" in error_type.lower():
            error_msg = f"{field_name} must be greater than the specified value."
        elif "less_than" in error_type.lower():
            error_msg = f"{field_name} must be less than the specified value."
        else:
            # Use the original message but make it more readable
            error_msg = f"{field_name}: {error_msg}"
        
        # Add to errors dict
        if field_name not in errors:
            errors[field_name] = []
        errors[field_name].append(error_msg)
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"errors": errors}
    )

# Include routers
app.include_router(schedule.router, prefix="/api/v1", tags=["scheduling"])

@app.get("/", tags=["health"])
async def root():
    """Root endpoint - API health check."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "healthy",
        "docs": "/docs"
    }

@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy"}

if __name__ == "__main__":
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload
    )
