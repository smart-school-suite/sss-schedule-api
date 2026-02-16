# 🎓 OR-Tools Scheduling API

A production-ready FastAPI microservice that generates optimized school timetables using Google OR-Tools CP-SAT solver.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)](https://fastapi.tiangolo.com/)
[![OR-Tools](https://img.shields.io/badge/OR--Tools-9.8-orange.svg)](https://developers.google.com/optimization)

## 📋 Overview

This API solves complex school scheduling problems with 30+ configurable constraints including:
- Teacher availability and preferences
- Hall capacity and type matching
- Course distribution and frequency
- Break periods and operational hours
- Load balancing and consecutive class limits

**Key Features:**
- ✅ Two scheduling modes: with/without teacher preferences
- ✅ Deterministic optimization (same input = same output)
- ✅ Handles infeasibility gracefully with detailed error messages
- ✅ Fast solving: ~5 seconds for 20 teachers, 10 halls, 50 courses
- ✅ Stateless design - no database required
- ✅ RESTful JSON API with OpenAPI documentation

## 🚀 Quick Start

### Installation

```bash
# Clone and navigate
git clone https://github.com/smart-school-suite/sss-schedule-api.git
cd sss-schedule-api

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
make install
# or: pip install -r requirements.txt

# Run server
make run
# or: uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

**Access the API:**
- 📚 API Docs: http://localhost:8080/docs
- 🏥 Health: http://localhost:8080/health

### Quick Test
```bash
curl -X POST http://localhost:8080/api/v1/schedule/without-preference \
  -H "Content-Type: application/json" \
  -d @examples/sample_request.json
```

### Testing with mocks (Swagger or curl)
Ready-to-use request bodies built from `mocks/constraints/` are in **`mocks/requests/`**:

| File | Use case |
|------|----------|
| `mocks/requests/minimal_valid.json` | Minimal valid request |
| `mocks/requests/break_period_mock.json` | Break period with `no_break_exceptions` + `day_exceptions` |
| `mocks/requests/required_joint_periods_mock.json` | Locked course periods (required_joint_course_periods) |
| `mocks/requests/soft_constraints_mock.json` | Soft constraints (teacher max hours, course requested slots, requested free period) |

- **In Swagger**: Open http://localhost:8080/docs → try an endpoint → paste the contents of any file above into the request body.
- **With curl**: `curl -X POST http://localhost:8080/api/v1/schedule/without-preference -H "Content-Type: application/json" -d @mocks/requests/minimal_valid.json`

See `mocks/requests/README.md` for details and more curl examples.

## 🎯 API Modes

This API supports two scheduling modes:

1. **Preference-Based Scheduling** (`/api/v1/schedule/with-preference`) - Respects teacher preferred teaching times
2. **Non-Preference Scheduling** (`/api/v1/schedule/without-preference`) - Focuses on feasibility only

## 📋 Features

### Hard Constraints (Must be satisfied)
- ✅ No overlapping scheduled slots
- ✅ No hall overlapping allowed
- ✅ Teacher busy period enforcement
- ✅ Hall busy period enforcement
- ✅ Break period enforcement
- ✅ Course type → Hall type matching (practical → lab, theory → lecture)
- ✅ Operational hours enforcement (per-day configurable)
- ✅ Standardized time slot intervals

### Soft Constraints (Optimization goals)
**Teacher Constraints:**
- Max daily/weekly teaching hours
- Minimum break between classes
- Even subject distribution
- Balanced workload
- Avoid split double periods

**Course Constraints:**
- Load proportionality (by credit hours)
- Avoid clustering of same course
- Minimum gap between sessions
- Room suitability matching
- Preferred time of day (morning/evening)
- Credit-hour density control
- Spread across week

**Hall Constraints:**
- Capacity limit enforcement
- Type suitability matching
- Change minimization (reduce movement)
- Usage balance across halls

**Time Constraints:**
- Max/min periods per day
- Balanced daily/weekly workload
- Avoid consecutive heavy subjects
- Consecutive period allowance
- Minimum gap between sessions
- Subject frequency per day limit

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
cd sss-schedule-api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Run the Server

```bash
# Development mode with auto-reload
uvicorn main:app --reload --port 8080

# Production mode
uvicorn main:app --host 0.0.0.0 --port 8080 --workers 4
```

### Run Tests

```bash
pytest tests/ -v
```

## 📡 API Endpoints

### 1. Generate Schedule (With Preference)

**POST** `/api/v1/schedule/with-preference`

Generates timetable considering teacher preferred teaching times.

### 2. Generate Schedule (Without Preference)

**POST** `/api/v1/schedule/without-preference`

Generates timetable ignoring teacher preferences.

### 3. Legacy Endpoint

**POST** `/api/schedule`

Backward-compatible endpoint (maps to without-preference mode).

## 📝 Request Format

See `api-details/request.json` for a complete example.

### Minimal Request

```json
{
  "teachers": [
    {
      "teacher_id": "t1",
      "name": "Dr. Smith"
    }
  ],
  "teacher_courses": [
    {
      "course_id": "c1",
      "course_title": "Mathematics",
      "course_credit": 4,
      "course_type": "theory",
      "course_hours": 40,
      "teacher_id": "t1",
      "teacher_name": "Dr. Smith"
    }
  ],
  "halls": [
    {
      "hall_id": "h1",
      "hall_name": "Room 101",
      "hall_capacity": 50,
      "hall_type": "lecture"
    }
  ],
  "break_period": {
    "start_time": "12:00",
    "end_time": "12:45",
    "daily": true
  },
  "operational_period": {
    "start_time": "08:00",
    "end_time": "16:00",
    "daily": true,
    "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
    "constrains": []
  },
  "teacher_busy_period": [],
  "teacher_prefered_teaching_period": [],
  "hall_busy_periods": [],
  "soft_constrains": {}
}
```

## 📤 Response Format

See `api-details/response.json` for a complete example.

```json
{
  "status": "OPTIMAL",
  "timetable": [
    {
      "day": "Monday",
      "slots": [
        {
          "day": "Monday",
          "start_time": "08:00",
          "end_time": "10:00",
          "teacher_id": "t1",
          "teacher_name": "Dr. Smith",
          "course_id": "c1",
          "course_name": "Mathematics",
          "hall_id": "h1",
          "hall_name": "Room 101",
          "break": false,
          "duration": "2h 0min"
        },
        {
          "day": "Monday",
          "break": true,
          "start_time": "12:00",
          "end_time": "12:45"
        }
      ]
    }
  ],
  "diagnostics": {
    "constraints": { "hard": [], "soft": [] },
    "summary": {
      "message": "All constraints satisfied.",
      "hard_constraints_met": true,
      "soft_constraints_met": true,
      "failed_soft_constraints_count": 0,
      "failed_hard_constraints_count": 0
    }
  },
  "metadata": { "solve_time_seconds": 2.5 },
  "messages": { "error_message": [] }
}
```

### Status Values

- `OPTIMAL` - All hard and soft constraints satisfied
- `PARTIAL` - All hard constraints met; one or more soft constraints not met (timetable valid, see `diagnostics.constraints.soft`)
- `ERROR` - One or more hard constraints not satisfied (see `diagnostics.constraints.hard`)
- Responses include `diagnostics` (constraints.hard / constraints.soft, summary) and `metadata.solve_time_seconds` per the functional spec.

## 🏗️ Architecture

```
sss-schedule-api/
├── main.py                 # FastAPI application entry
├── models/
│   └── schemas.py          # Pydantic data models
├── routers/
│   └── schedule.py         # API endpoints
├── service/
│   ├── ortools_solver.py   # OR-Tools CP-SAT solver
│   └── scheduler.py        # Legacy scheduler
├── tests/
│   └── test_api.py         # API tests
├── api-details/
│   ├── request.json        # Sample request
│   ├── response.json       # Sample response
│   └── timetable_constraints.md  # Constraint documentation
├── requirements.txt
└── README.md
```

## 🔧 Configuration

### Solver Parameters

Edit in `service/ortools_solver.py`:

```python
ORToolsScheduler(
    respect_preferences=True,    # Enable preference-based scheduling
    time_limit_seconds=30        # Solver timeout (seconds)
)
```

### Deterministic Behavior

The solver uses a fixed random seed (42) and single-threaded search to ensure identical inputs produce identical outputs.

## ⚠️ Implementation Status

### ✅ Completed
- [x] Complete schema rewrite matching API contract
- [x] Request/Response models with nested structures; diagnostics (hard/soft), summary, metadata
- [x] Two versioned API endpoints (with-preference / without-preference)
- [x] OR-Tools solver: variables, hard constraints, solve, solution extraction
- [x] Operational period parsing (per-day configuration)
- [x] Break period (including `no_break_exceptions`, `day_exceptions`); break slots in output
- [x] Time slot generation with 15-minute alignment
- [x] Input validation
- [x] Course type → Hall type matching
- [x] **Hard constraints:** course frequency, no teacher/hall double-booking, teacher/hall busy blocking, break blocking, required_joint_course_periods
- [x] **Soft constraints (post-solve):** teacher_max_daily_hours, teacher_max_weekly_hours, schedule_max_periods_per_day, schedule_max_free_periods_per_day, course_max_daily_frequency, course_requested_time_slots, teacher_requested_time_windows, hall_requested_time_windows, requested_assignments, requested_free_periods
- [x] Teacher preference matching (weighted objective for with-preference endpoint)
- [x] Solution extraction: map variables to slots, durations, group by day, include break slots
- [x] Status OPTIMAL / PARTIAL / ERROR and diagnostic format per functional spec
- [x] Test suite and mocks/requests for Swagger and curl testing

### 🔲 Optional / Future
- [ ] Operational period / period duration: accept doc names `day_exceptions`, `duration_minutes` in request (in addition to current schema)
- [ ] Hall busy periods: add `day` field for per-day unavailability
- [ ] Additional soft constraints (e.g. consecutive class limits, gap minimization) if required
- [ ] Student class/group support, multi-class scheduling, warm-start, solution quality metrics

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_api.py::test_with_preference_endpoint_with_sample_data -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

## 📚 Documentation

- **API Specification**: `new.md` - High-level requirements
- **Constraint Definitions**: `api-details/timetable_constraints.md`
- **Integration Guide**: `ORTOOLS_INTEGRATION.md`
- **Sample Request**: `api-details/request.json`
- **Sample Response**: `api-details/response.json`

## 🐛 Known Issues & Limitations

1. **No student group modeling** - Current API doesn't include student class/section data
2. **Session duration calculation** - Sessions per week derived from `course_credit`; can be refined using `course_hours` and semester length
3. **Performance** - Variable creation and filtering can be optimized for very large instances

## 🤝 Contributing

Possible next steps:

1. Add optional request fields for doc-style naming (`day_exceptions`, `duration_minutes`) where applicable
2. Extend soft constraints (e.g. consecutive limits, gap minimization) if product requires them
3. Add more test cases using `mocks/requests/` and assert diagnostic shapes against `mocks/diagnostics/`
4. Optimize solver for large schools (many teachers, halls, courses)

## 📝 License

[Add license information]

## 📧 Contact

[Add contact information]

---

**Note**: This is a work-in-progress implementation. The core architecture and API contracts are complete, but constraint modeling requires additional development to handle all 30+ soft constraints specified in the requirements.
