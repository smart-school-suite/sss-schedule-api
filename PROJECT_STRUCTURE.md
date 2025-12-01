# 📂 Project Structure

```
sss-schedule-api/
├── config/                     # Configuration management
│   ├── __init__.py
│   └── settings.py            # Application settings
├── docs/                       # Documentation
│   ├── CONSTRAINT_IMPLEMENTATION_GUIDE.md
│   ├── IMPLEMENTATION_ROADMAP.md
│   ├── ORTOOLS_INTEGRATION.md
│   ├── original_spec.md
│   └── timetable_constraints.md
├── examples/                   # Sample requests and responses
│   ├── sample_request.json
│   └── sample_response.json
├── models/                     # Data models
│   ├── __init__.py
│   └── schemas.py             # Pydantic models
├── routers/                    # API routes
│   ├── __init__.py
│   └── schedule.py            # Scheduling endpoints
├── service/                    # Business logic
│   ├── __init__.py
│   ├── ortools_solver.py      # OR-Tools CP-SAT solver
│   └── scheduler.py           # Legacy scheduler (archived)
├── tests/                      # Test suite
│   ├── __init__.py
│   └── test_api.py            # API integration tests
├── .dockerignore              # Docker ignore patterns
├── .env.example               # Example environment variables
├── .gitignore                 # Git ignore patterns
├── docker-compose.yml         # Docker Compose configuration
├── Dockerfile                 # Docker image definition
├── main.py                    # FastAPI application entry point
├── Makefile                   # Development commands
├── pyproject.toml             # Python project metadata
├── README.md                  # Main documentation
├── requirements.txt           # Python dependencies
└── setup.cfg                  # Tool configurations
```

## Key Files

### Core Application
- **`main.py`**: FastAPI app initialization, middleware, and routing
- **`config/settings.py`**: Centralized configuration using Pydantic settings
- **`models/schemas.py`**: Request/response data models matching API spec

### Solver Implementation
- **`service/ortools_solver.py`**: Main CP-SAT solver with constraint modeling
- **`routers/schedule.py`**: API endpoints for with/without preferences

### Configuration
- **`.env.example`**: Template for environment variables
- **`requirements.txt`**: Pinned Python dependencies
- **`pyproject.toml`**: Black, Ruff, and project metadata

### Deployment
- **`Dockerfile`**: Production-ready container image
- **`docker-compose.yml`**: Local development with Docker
- **`Makefile`**: Common development tasks

## Development Workflow

```bash
# Install dependencies
make install

# Run tests
make test

# Format code
make format

# Run linter
make lint

# Run development server
make run

# Clean cache
make clean
```

## Adding New Constraints

1. Add constraint parameter to `SoftConstraints` in `models/schemas.py`
2. Implement constraint logic in `service/ortools_solver.py`
3. Update `docs/CONSTRAINT_IMPLEMENTATION_GUIDE.md`
4. Add test case in `tests/test_api.py`
5. Update API documentation

## Architecture Principles

- **Stateless**: No database, all data in request/response
- **Deterministic**: Same input always produces same output
- **Configurable**: All timeouts and parameters via environment/config
- **Testable**: Pure functions, dependency injection ready
- **Documented**: OpenAPI/Swagger + markdown docs
