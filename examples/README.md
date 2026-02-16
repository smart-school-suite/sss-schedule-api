# Example Payloads

This directory contains example request payloads demonstrating different scheduling scenarios.

## Files

### 1. request_with_preferences.json
**Purpose:** Complete example showing how to use teacher preferences and soft constraints  
**Use with endpoint:** `POST /schedule/with-preference`

**Features:**
- ✅ 3 teacher preferred teaching periods defined
- ✅ 2 hall busy periods (equipment maintenance, other bookings)
- ✅ Break period with exceptions (no break on Saturday, custom break time on Friday)
- ✅ Operational period with day exception (Friday closes early at 15:00)
- ✅ Soft constraints including:
  - Teacher max daily/weekly hours with exceptions
  - Schedule max periods per day
  - Course requested time slots
  - Requested free periods
- ✅ Required joint course periods (Physics Lab locked to specific times)
- ✅ Period duration set to 60 minutes

**Scenario:**
A university scheduling 3 courses across 5 weekdays with:
- Dr. Smith prefers morning on Monday and afternoon on Wednesday
- Prof. Johnson prefers Tuesday 10:00-15:00
- Physics Lab must be scheduled at fixed times (Tuesday 10-12, Thursday 14-16)
- Friday has shorter hours (ends at 15:00)
- Math course requested for Monday 09:00 and Wednesday 10:00

---

### 2. request_without_preferences.json
**Purpose:** Simplified example without teacher time preferences  
**Use with endpoint:** `POST /schedule/without-preference`

**Features:**
- ❌ No teacher preferred teaching periods (empty array)
- ✅ 2 hall busy periods
- ✅ Simple break period (12:00-13:00 daily)
- ✅ Operational period with day exception (Friday closes early)
- ✅ Minimal soft constraints (just max hours and max periods)
- ✅ Required joint course periods (same Physics Lab requirements)
- ✅ Period duration set to 60 minutes

**Scenario:**
Same course setup but scheduler has full flexibility on when to assign teachers (no preference constraints).

---

## Key Differences

| Feature | With Preferences | Without Preferences |
|---------|-----------------|---------------------|
| `teacher_prefered_teaching_period` | 3 preferences | Empty array |
| `break_period` exceptions | Has no_break + day_exceptions | Simple daily break |
| Soft constraints | Comprehensive | Minimal |
| Course requested slots | Yes | No |
| Requested free periods | Yes | No |

---

## Usage Examples

### Using cURL

**With Preferences:**
```bash
curl -X POST "http://localhost:8000/schedule/with-preference" \
  -H "Content-Type: application/json" \
  -d @examples/request_with_preferences.json
```

**Without Preferences:**
```bash
curl -X POST "http://localhost:8000/schedule/without-preference" \
  -H "Content-Type: application/json" \
  -d @examples/request_without_preferences.json
```

### Using Python

```python
import requests
import json

# With preferences
with open('examples/request_with_preferences.json') as f:
    payload = json.load(f)

response = requests.post(
    'http://localhost:8000/schedule/with-preference',
    json=payload
)
print(response.json())

# Without preferences
with open('examples/request_without_preferences.json') as f:
    payload = json.load(f)

response = requests.post(
    'http://localhost:8000/schedule/without-preference',
    json=payload
)
print(response.json())
```

---

## Expected Behavior

### With Preferences Endpoint
- Attempts to schedule courses during teacher preferred time windows
- Tries to honor course requested time slots
- Creates requested free periods when possible
- Returns diagnostics if preferences cannot be met
- May return PARTIAL status if some soft constraints fail

### Without Preferences Endpoint
- Ignores teacher time preferences completely
- Focuses on feasibility and hard constraints only
- Typically faster to solve
- More likely to return OPTIMAL status

---

## Other Example Files

- **sample_request.json** - Original comprehensive example
- **sample_response.json** - Example successful response

---

## Data Details

### Teachers
- **Dr. Smith** (a1b2c3d4-e5f6-7890-abcd-ef1234567890)
  - Course: Advanced Mathematics (45 hours, theory)
  - Busy: Monday 08:00-09:00
  - Prefers: Monday morning, Wednesday afternoon

- **Prof. Johnson** (b2c3d4e5-f6a7-8901-bcde-f12345678901)
  - Course: Physics Laboratory (30 hours, practical)
  - Prefers: Tuesday 10:00-15:00

- **Dr. Williams** (c3d4e5f6-a7b8-9012-cdef-123456789012)
  - Course: General Chemistry (45 hours, theory)

### Halls
- **Main Lecture Hall** (200 capacity, lecture type)
  - Busy: Friday 16:00-17:00
- **Physics Lab** (40 capacity, lab type)
  - Busy: Monday 08:00-09:00
- **Small Classroom** (30 capacity, lecture type)

### Time Parameters
- **Operational Hours:** 08:00-17:00 (except Friday: 08:00-15:00)
- **Break Period:** 12:00-13:00 daily (except Saturday, Friday 13:00-14:00 in preferences example)
- **Slot Duration:** 60 minutes
- **Active Days:** Monday-Friday

---

## Validation

Both files are validated against the Pydantic schema. To verify:

```bash
python validate_mocks.py
```

Or manually:
```python
from models.schemas import SchedulingRequest
import json

with open('examples/request_with_preferences.json') as f:
    req = SchedulingRequest(**json.load(f))
    print("✅ Valid")
```
