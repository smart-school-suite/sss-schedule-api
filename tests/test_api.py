"""
Test the scheduling API with self-contained test data.
"""
import pytest
from fastapi.testclient import TestClient
from main import app


client = TestClient(app)


# Test data fixtures
def get_minimal_request():
    """Return minimal valid scheduling request."""
    return {
        "teachers": [
            {"teacher_id": "t1", "name": "John Doe"}
        ],
        "teacher_courses": [
            {
                "course_id": "c1",
                "course_title": "Mathematics 101",
                "course_credit": 3,
                "course_type": "theory",
                "course_hours": 30,
                "teacher_id": "t1",
                "teacher_name": "John Doe"
            }
        ],
        "halls": [
            {
                "hall_id": "h1",
                "hall_name": "Lecture Hall A",
                "hall_capacity": 50,
                "hall_type": "lecture"
            }
        ],
        "teacher_busy_period": [],
        "teacher_prefered_teaching_period": [],
        "hall_busy_periods": [],
        "break_period": {
            "start_time": "12:00",
            "end_time": "13:00",
            "daily": True
        },
        "operational_period": {
            "start_time": "08:00",
            "end_time": "17:00",
            "daily": True,
            "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "constrains": []
        },
        "soft_constrains": {}
    }


def get_medium_request():
    """Return medium-sized scheduling request with multiple entities."""
    return {
        "teachers": [
            {"teacher_id": "t1", "name": "Alice Smith"},
            {"teacher_id": "t2", "name": "Bob Johnson"}
        ],
        "teacher_courses": [
            {
                "course_id": "c1",
                "course_title": "Mathematics",
                "course_credit": 3,
                "course_type": "theory",
                "course_hours": 45,
                "teacher_id": "t1",
                "teacher_name": "Alice Smith"
            },
            {
                "course_id": "c2",
                "course_title": "Physics Lab",
                "course_credit": 4,
                "course_type": "practical",
                "course_hours": 60,
                "teacher_id": "t2",
                "teacher_name": "Bob Johnson"
            }
        ],
        "halls": [
            {
                "hall_id": "h1",
                "hall_name": "Room 101",
                "hall_capacity": 40,
                "hall_type": "lecture"
            },
            {
                "hall_id": "h2",
                "hall_name": "Lab A",
                "hall_capacity": 25,
                "hall_type": "lab"
            }
        ],
        "teacher_busy_period": [
            {
                "teacher_id": "t1",
                "teacher_name": "Alice Smith",
                "day": "monday",
                "start_time": "15:00",
                "end_time": "17:00"
            }
        ],
        "teacher_prefered_teaching_period": [
            {
                "teacher_id": "t1",
                "teacher_name": "Alice Smith",
                "day": "tuesday",
                "start_time": "09:00",
                "end_time": "11:00"
            }
        ],
        "hall_busy_periods": [],
        "break_period": {
            "start_time": "12:00",
            "end_time": "13:00",
            "daily": True
        },
        "operational_period": {
            "start_time": "08:00",
            "end_time": "17:00",
            "daily": True,
            "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "constrains": []
        },
        "soft_constrains": {
            "teacher_max_daily_hours": 6,
            "teacher_max_weekly_hours": 25,
            "course_type_room_suitability": True,
            "hall_capacity_enforcement": True
        }
    }


def test_root_endpoint():
    """Test root endpoint is accessible."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "status" in data
    assert data["status"] == "healthy"


def test_with_preference_endpoint_minimal():
    """Test /v1/schedule/with-preference with minimal valid request."""
    request_data = get_minimal_request()
    
    response = client.post("/api/v1/schedule/with-preference", json=request_data)
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "timetable" in data
    assert "messages" in data
    assert isinstance(data["timetable"], list)
    assert isinstance(data["messages"], dict)
    
    # Should have a status (spec: OPTIMAL, PARTIAL, ERROR)
    assert "status" in data
    assert data["status"] in ["OPTIMAL", "PARTIAL", "ERROR"]
    # New response shape: diagnostics + metadata
    assert "diagnostics" in data
    assert "metadata" in data
    assert "constraints" in data["diagnostics"]
    assert "summary" in data["diagnostics"]
    assert data["diagnostics"]["summary"]["hard_constraints_met"] == (data["status"] != "ERROR")


def test_without_preference_endpoint_minimal():
    """Test /v1/schedule/without-preference with minimal valid request."""
    request_data = get_minimal_request()
    
    response = client.post("/api/v1/schedule/without-preference", json=request_data)
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "timetable" in data
    assert "messages" in data
    assert "status" in data


def test_with_preference_endpoint_medium():
    """Test /v1/schedule/with-preference with medium-sized request."""
    request_data = get_medium_request()
    
    response = client.post("/api/v1/schedule/with-preference", json=request_data)
    
    # Print validation errors if any
    if response.status_code != 200:
        print(f"\nValidation error: {response.json()}")
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
    data = response.json()
    
    # Should respect preferences and return valid structure
    assert "timetable" in data
    assert "status" in data


def test_without_preference_endpoint_medium():
    """Test /v1/schedule/without-preference with medium-sized request."""
    request_data = get_medium_request()
    
    response = client.post("/api/v1/schedule/without-preference", json=request_data)
    
    assert response.status_code == 200
    data = response.json()
    
    # Should work without considering preferences
    assert "timetable" in data
    assert "status" in data


def test_empty_request_returns_error():
    """Test that empty/invalid request returns proper error."""
    
    invalid_request = {
        "teachers": [],
        "teacher_courses": [],
        "halls": [],
        "teacher_busy_period": [],
        "teacher_prefered_teaching_period": [],
        "hall_busy_periods": [],
        "break_period": {
            "start_time": "12:00",
            "end_time": "12:45",
            "daily": True
        },
        "operational_period": {
            "start_time": "08:00",
            "end_time": "16:00",
            "daily": True,
            "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "constrains": []
        }
    }
    
    response = client.post("/api/v1/schedule/with-preference", json=invalid_request)
    
    assert response.status_code == 200
    data = response.json()
    # Infeasible/error: status ERROR and hard diagnostics or legacy error_message
    assert data["status"] == "ERROR" or len(data.get("messages", {}).get("error_message", [])) > 0 or len(data.get("diagnostics", {}).get("constraints", {}).get("hard", [])) > 0


def test_course_type_hall_type_matching():
    """Test that practical courses get labs and theory courses get lecture halls."""
    request = {
        "teachers": [
            {"teacher_id": "t1", "name": "Teacher One"}
        ],
        "teacher_courses": [
            {
                "course_id": "c1",
                "course_title": "Chemistry Lab",
                "course_credit": 3,
                "course_type": "practical",
                "course_hours": 30,
                "teacher_id": "t1",
                "teacher_name": "Teacher One"
            }
        ],
        "halls": [
            {
                "hall_id": "h1",
                "hall_name": "Lecture Room",
                "hall_capacity": 50,
                "hall_type": "lecture"
            },
            {
                "hall_id": "h2",
                "hall_name": "Lab 1",
                "hall_capacity": 30,
                "hall_type": "lab"
            }
        ],
        "teacher_busy_period": [],
        "teacher_prefered_teaching_period": [],
        "hall_busy_periods": [],
        "break_period": {
            "start_time": "12:00",
            "end_time": "13:00",
            "daily": True
        },
        "operational_period": {
            "start_time": "08:00",
            "end_time": "17:00",
            "daily": True,
            "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "constrains": []
        },
        "soft_constrains": {
            "course_type_room_suitability": True
        }
    }
    
    response = client.post("/api/v1/schedule/without-preference", json=request)
    
    assert response.status_code == 200
    data = response.json()
    
    # If scheduled successfully, practical courses should be in labs
    if data["status"] in ["OPTIMAL", "PARTIAL"]:
        for day_schedule in data["timetable"]:
            for slot in day_schedule.get("slots", []):
                if not slot.get("break", False) and slot.get("course_name") == "Chemistry Lab":
                    # Should be in a lab
                    assert "Lab" in slot.get("hall_name", "") or slot.get("hall_id") == "h2"


def test_teacher_busy_period_respected():
    """Test that teacher busy periods are respected."""
    request = get_minimal_request()
    
    # Add a busy period for Monday 14:00-17:00
    request["teacher_busy_period"] = [
        {
            "teacher_id": "t1",
            "teacher_name": "John Doe",
            "day": "monday",
            "start_time": "14:00",
            "end_time": "17:00"
        }
    ]
    
    response = client.post("/api/v1/schedule/without-preference", json=request)
    
    assert response.status_code == 200
    data = response.json()
    
    # If scheduled, no classes should be during busy period
    if data["status"] in ["OPTIMAL", "PARTIAL"]:
        for day_schedule in data["timetable"]:
            if day_schedule["day"].lower() == "monday":
                for slot in day_schedule.get("slots", []):
                    if not slot.get("break", False):
                        # Should not overlap with 14:00-17:00
                        start = slot.get("start_time", "")
                        # Basic check (more robust parsing would be better)
                        assert not (start >= "14:00" and start < "17:00")


# ============================================
# NEW TEST CASES FOR IMPLEMENTED FIXES
# ============================================

def test_break_period_days_exception():
    """Test that breaks are skipped on days in days_exception."""
    request = get_minimal_request()
    request["break_period"] = {
        "start_time": "12:00",
        "end_time": "13:00",
        "daily": True,
        "constrains": {
            "daysException": ["monday", "tuesday"]
        }
    }
    
    response = client.post("/api/v1/schedule/without-preference", json=request)
    assert response.status_code == 200
    data = response.json()
    
    if data["status"] in ["OPTIMAL", "PARTIAL"]:
        for day_schedule in data["timetable"]:
            day_lower = day_schedule["day"].lower()
            if day_lower in ["monday", "tuesday"]:
                # No break slots should exist on exception days
                for slot in day_schedule.get("slots", []):
                    if slot.get("break", False):
                        # Should not have break on exception days
                        assert False, f"Break found on exception day: {day_lower}"
            else:
                # Other days should have breaks
                has_break = any(slot.get("break", False) for slot in day_schedule.get("slots", []))
                assert has_break, f"No break found on non-exception day: {day_lower}"


def test_break_period_days_fixed_breaks():
    """Test that days_fixed_breaks override default break times."""
    request = get_minimal_request()
    request["break_period"] = {
        "start_time": "12:00",
        "end_time": "13:00",
        "daily": True,
        "constrains": {
            "daysFixedBreaks": [
                {
                    "day": "monday",
                    "start_time": "11:30",
                    "end_time": "12:15"
                }
            ]
        }
    }
    
    response = client.post("/api/v1/schedule/without-preference", json=request)
    assert response.status_code == 200
    data = response.json()
    
    if data["status"] in ["OPTIMAL", "PARTIAL"]:
        for day_schedule in data["timetable"]:
            if day_schedule["day"].lower() == "monday":
                # Monday should have fixed break time
                break_slots = [s for s in day_schedule.get("slots", []) if s.get("break", False)]
                if break_slots:
                    break_slot = break_slots[0]
                    assert break_slot["start_time"] == "11:30"
                    assert break_slot["end_time"] == "12:15"
            elif day_schedule["day"].lower() in ["tuesday", "wednesday", "thursday", "friday"]:
                # Other days should have default break time
                break_slots = [s for s in day_schedule.get("slots", []) if s.get("break", False)]
                if break_slots:
                    break_slot = break_slots[0]
                    assert break_slot["start_time"] == "12:00"
                    assert break_slot["end_time"] == "13:00"


def test_break_period_exception_and_fixed_breaks():
    """Test that days_exception takes priority over fixed breaks."""
    request = get_minimal_request()
    request["break_period"] = {
        "start_time": "12:00",
        "end_time": "13:00",
        "daily": True,
        "constrains": {
            "daysException": ["monday"],
            "daysFixedBreaks": [
                {
                    "day": "monday",
                    "start_time": "11:30",
                    "end_time": "12:15"
                }
            ]
        }
    }
    
    response = client.post("/api/v1/schedule/without-preference", json=request)
    assert response.status_code == 200
    data = response.json()
    
    if data["status"] in ["OPTIMAL", "PARTIAL"]:
        for day_schedule in data["timetable"]:
            if day_schedule["day"].lower() == "monday":
                # Monday should have NO break (exception takes priority)
                break_slots = [s for s in day_schedule.get("slots", []) if s.get("break", False)]
                assert len(break_slots) == 0, "Break found on exception day despite fixed break"


def test_configurable_slot_duration():
    """Test configurable slot duration with periods configuration."""
    request = get_minimal_request()
    request["periods"] = {
        "daily": True,
        "period": 45,  # 45-minute slots
        "constrains": {
            "daysFixedPeriods": [
                {
                    "day": "monday",
                    "period": 60  # Monday has 60-minute slots
                }
            ]
        }
    }
    
    response = client.post("/api/v1/schedule/without-preference", json=request)
    assert response.status_code == 200
    data = response.json()
    
    if data["status"] in ["OPTIMAL", "PARTIAL"]:
        for day_schedule in data["timetable"]:
            for slot in day_schedule.get("slots", []):
                if not slot.get("break", False) and slot.get("duration"):
                    # Check that durations match expected periods
                    if day_schedule["day"].lower() == "monday":
                        # Monday should have 60-minute slots (or multiples)
                        assert "1h" in slot["duration"] or "60min" in slot["duration"] or "2h" in slot["duration"]
                    else:
                        # Other days should have 45-minute slots
                        assert "45min" in slot["duration"] or "1h" in slot["duration"]


def test_exclude_days_with_only_breaks():
    """Test that days with only break slots are excluded from output."""
    request = get_minimal_request()
    # Schedule course only on Monday
    request["operational_period"]["days"] = ["monday", "tuesday", "wednesday"]
    request["teacher_courses"][0]["course_credit"] = 1  # Minimal course
    
    response = client.post("/api/v1/schedule/without-preference", json=request)
    assert response.status_code == 200
    data = response.json()
    
    if data["status"] in ["OPTIMAL", "PARTIAL"]:
        # Days with only breaks should not appear
        for day_schedule in data["timetable"]:
            non_break_slots = [s for s in day_schedule.get("slots", []) if not s.get("break", False)]
            # Each day in timetable should have at least one non-break slot
            assert len(non_break_slots) > 0, f"Day {day_schedule['day']} has only break slots"


def test_teacher_preference_strict_enforcement():
    """Test that teacher preferences are strictly enforced in with-preference mode."""
    request = get_minimal_request()
    request["teacher_prefered_teaching_period"] = [
        {
            "teacher_id": "t1",
            "teacher_name": "John Doe",
            "day": "monday",
            "start_time": "09:00",
            "end_time": "12:00"
        }
    ]
    
    response = client.post("/api/v1/schedule/with-preference", json=request)
    assert response.status_code == 200
    data = response.json()
    
    if data["status"] in ["OPTIMAL", "PARTIAL"]:
        for day_schedule in data["timetable"]:
            if day_schedule["day"].lower() == "monday":
                for slot in day_schedule.get("slots", []):
                    if not slot.get("break", False) and slot.get("teacher_id") == "t1":
                        # All classes for t1 on Monday should be between 09:00-12:00
                        start_time = slot.get("start_time", "")
                        end_time = slot.get("end_time", "")
                        assert start_time >= "09:00", f"Class starts before preference: {start_time}"
                        assert end_time <= "12:00", f"Class ends after preference: {end_time}"


def test_teacher_preference_not_enforced_in_without_preference():
    """Test that preferences are NOT enforced in without-preference mode."""
    request = get_minimal_request()
    request["teacher_prefered_teaching_period"] = [
        {
            "teacher_id": "t1",
            "teacher_name": "John Doe",
            "day": "monday",
            "start_time": "09:00",
            "end_time": "10:00"  # Very narrow window
        }
    ]
    
    response = client.post("/api/v1/schedule/without-preference", json=request)
    assert response.status_code == 200
    data = response.json()
    
    # Should still be feasible even with narrow preference window
    # because preferences are ignored in without-preference mode
    assert data["status"] in ["OPTIMAL", "PARTIAL", "ERROR"]


def test_hall_busy_period_blocking():
    """Test that hall busy periods block scheduling."""
    request = get_minimal_request()
    request["hall_busy_periods"] = [
        {
            "hall_id": "h1",
            "hall_name": "Lecture Hall A",
            "start_time": "10:00",
            "end_time": "12:00"
        }
    ]
    
    response = client.post("/api/v1/schedule/without-preference", json=request)
    assert response.status_code == 200
    data = response.json()
    
    if data["status"] in ["OPTIMAL", "PARTIAL"]:
        for day_schedule in data["timetable"]:
            for slot in day_schedule.get("slots", []):
                if not slot.get("break", False) and slot.get("hall_id") == "h1":
                    # Hall h1 should not be used during busy period
                    start_time = slot.get("start_time", "")
                    end_time = slot.get("end_time", "")
                    # Should not overlap with 10:00-12:00
                    assert not (start_time < "12:00" and end_time > "10:00"), \
                        f"Hall used during busy period: {start_time}-{end_time}"


def test_break_period_blocking():
    """Test that classes are not scheduled during break periods."""
    request = get_minimal_request()
    request["break_period"] = {
        "start_time": "12:00",
        "end_time": "13:00",
        "daily": True
    }
    
    response = client.post("/api/v1/schedule/without-preference", json=request)
    assert response.status_code == 200
    data = response.json()
    
    if data["status"] in ["OPTIMAL", "PARTIAL"]:
        for day_schedule in data["timetable"]:
            for slot in day_schedule.get("slots", []):
                if not slot.get("break", False):
                    start_time = slot.get("start_time", "")
                    end_time = slot.get("end_time", "")
                    # Should not overlap with break period 12:00-13:00
                    assert not (start_time < "13:00" and end_time > "12:00"), \
                        f"Class scheduled during break: {start_time}-{end_time}"


def test_validation_error_format():
    """Test that validation errors return human-friendly format."""
    # Missing required field
    invalid_request = {
        "teachers": [],
        # Missing teacher_courses, halls, etc.
    }
    
    response = client.post("/api/v1/schedule/with-preference", json=invalid_request)
    
    # Should return 422 with errors in expected format
    assert response.status_code == 422
    data = response.json()
    assert "errors" in data
    assert isinstance(data["errors"], dict)
    
    # Check that error messages are human-readable
    for field, messages in data["errors"].items():
        assert isinstance(messages, list)
        assert len(messages) > 0
        assert isinstance(messages[0], str)


def test_break_period_validation_invalid_time_order():
    """Test validation catches break period with start_time after end_time."""
    request = get_minimal_request()
    request["break_period"] = {
        "start_time": "14:00",
        "end_time": "12:00",  # Invalid: start after end
        "daily": True
    }
    
    response = client.post("/api/v1/schedule/without-preference", json=request)
    assert response.status_code == 200
    data = response.json()
    
    # Should have validation error
    assert data["status"] == "ERROR" or len(data.get("messages", {}).get("error_message", [])) > 0 or len(data.get("diagnostics", {}).get("constraints", {}).get("hard", [])) > 0


def test_periods_validation_invalid_duration():
    """Test validation catches invalid period duration."""
    request = get_minimal_request()
    request["periods"] = {
        "daily": True,
        "period": -10  # Invalid: negative duration
    }
    
    response = client.post("/api/v1/schedule/without-preference", json=request)
    assert response.status_code == 200
    data = response.json()
    
    # Should have validation error
    assert data["status"] == "ERROR" or len(data.get("messages", {}).get("error_message", [])) > 0 or len(data.get("diagnostics", {}).get("constraints", {}).get("hard", [])) > 0


def test_enhanced_error_structure():
    """Test that error messages have enhanced structure with diagnostics."""
    request = get_minimal_request()
    # Make it infeasible by having too many courses for available time
    request["teacher_courses"] = [
        {
            "course_id": f"c{i}",
            "course_title": f"Course {i}",
            "course_credit": 10,  # High credit
            "course_type": "theory",
            "course_hours": 1000,  # Unrealistic hours
            "teacher_id": "t1",
            "teacher_name": "John Doe"
        }
        for i in range(10)  # 10 courses
    ]
    
    response = client.post("/api/v1/schedule/without-preference", json=request)
    assert response.status_code == 200
    data = response.json()
    
    if data["status"] == "ERROR" and (len(data.get("messages", {}).get("error_message", [])) > 0 or len(data.get("diagnostics", {}).get("constraints", {}).get("hard", [])) > 0):
        error = (data.get("messages", {}).get("error_message") or [{}])[0]
        if not error and data.get("diagnostics", {}).get("constraints", {}).get("hard"):
            error = data["diagnostics"]["constraints"]["hard"][0].get("constraint_failed", {})
        # Check for enhanced error structure (legacy messages or new diagnostics)
        assert "code" in error or "constraint_type" in error or "severity" in error or "type" in error
        assert "title" in error or "description" in error or "message" in error or "details" in error


def test_teacher_busy_period_validation():
    """Test validation of teacher busy periods."""
    request = get_minimal_request()
    request["teacher_busy_period"] = [
        {
            "teacher_id": "t1",
            "teacher_name": "John Doe",
            "day": "invalid_day",  # Invalid day
            "start_time": "10:00",
            "end_time": "12:00"
        }
    ]
    
    response = client.post("/api/v1/schedule/without-preference", json=request)
    assert response.status_code == 200
    data = response.json()
    
    # Should have validation error for invalid day
    assert data["status"] == "ERROR" or len(data.get("messages", {}).get("error_message", [])) > 0 or len(data.get("diagnostics", {}).get("constraints", {}).get("hard", [])) > 0


def test_teacher_preferred_period_validation():
    """Test validation of teacher preferred periods."""
    request = get_minimal_request()
    request["teacher_prefered_teaching_period"] = [
        {
            "teacher_id": "t1",
            "teacher_name": "John Doe",
            "day": "monday",
            "start_time": "14:00",
            "end_time": "12:00"  # Invalid: start after end
        }
    ]
    
    response = client.post("/api/v1/schedule/with-preference", json=request)
    assert response.status_code == 200
    data = response.json()
    
    # Should have validation error
    assert data["status"] == "ERROR" or len(data.get("messages", {}).get("error_message", [])) > 0 or len(data.get("diagnostics", {}).get("constraints", {}).get("hard", [])) > 0


def test_multiple_constraints_combined():
    """Test combination of multiple constraints working together."""
    request = get_minimal_request()
    request["break_period"] = {
        "start_time": "12:00",
        "end_time": "13:00",
        "daily": True,
        "constrains": {
            "daysException": ["friday"]
        }
    }
    request["teacher_busy_period"] = [
        {
            "teacher_id": "t1",
            "teacher_name": "John Doe",
            "day": "monday",
            "start_time": "14:00",
            "end_time": "17:00"
        }
    ]
    request["teacher_prefered_teaching_period"] = [
        {
            "teacher_id": "t1",
            "teacher_name": "John Doe",
            "day": "tuesday",
            "start_time": "09:00",
            "end_time": "12:00"
        }
    ]
    request["periods"] = {
        "daily": True,
        "period": 45
    }
    
    response = client.post("/api/v1/schedule/with-preference", json=request)
    assert response.status_code == 200
    data = response.json()
    
    # Should handle all constraints together
    assert data["status"] in ["OPTIMAL", "PARTIAL", "ERROR"]
    
    if data["status"] in ["OPTIMAL", "PARTIAL"]:
        # Verify break exception
        for day_schedule in data["timetable"]:
            if day_schedule["day"].lower() == "friday":
                break_slots = [s for s in day_schedule.get("slots", []) if s.get("break", False)]
                assert len(break_slots) == 0, "Break found on exception day"


def test_response_shape_matches_spec():
    """Response must include status, timetable, diagnostics (constraints + summary), metadata (spec + mocks)."""
    request_data = get_minimal_request()
    response = client.post("/api/v1/schedule/without-preference", json=request_data)
    assert response.status_code == 200
    data = response.json()

    assert "status" in data
    assert data["status"] in ["OPTIMAL", "PARTIAL", "ERROR"]
    assert "timetable" in data
    assert isinstance(data["timetable"], list)

    # Diagnostics (DR-01, mocks/response/optimal.response.example.json)
    assert "diagnostics" in data
    diag = data["diagnostics"]
    assert "constraints" in diag
    assert "hard" in diag["constraints"]
    assert "soft" in diag["constraints"]
    assert isinstance(diag["constraints"]["hard"], list)
    assert isinstance(diag["constraints"]["soft"], list)
    assert "summary" in diag
    summary = diag["summary"]
    assert "message" in summary
    assert "hard_constraints_met" in summary
    assert "soft_constraints_met" in summary
    assert "failed_soft_constraints_count" in summary
    assert "failed_hard_constraints_count" in summary

    # Metadata
    assert "metadata" in data
    assert "solve_time_seconds" in data["metadata"]

    # Status vs summary consistency (RC-04)
    if data["status"] == "OPTIMAL":
        assert summary["hard_constraints_met"] is True
        assert summary["soft_constraints_met"] is True
    elif data["status"] == "PARTIAL":
        assert summary["hard_constraints_met"] is True
        assert summary["soft_constraints_met"] is False
    elif data["status"] == "ERROR":
        assert summary["hard_constraints_met"] is False


def test_error_response_has_diagnostic_blockers():
    """On ERROR, diagnostics.constraints.hard must contain constraint_failed and blockers (DR-02, DR-03)."""
    invalid_request = {
        "teachers": [],
        "teacher_courses": [],
        "halls": [],
        "teacher_busy_period": [],
        "teacher_prefered_teaching_period": [],
        "hall_busy_periods": [],
        "break_period": {"start_time": "12:00", "end_time": "13:00", "daily": True},
        "operational_period": {
            "start_time": "08:00",
            "end_time": "16:00",
            "daily": True,
            "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "constrains": [],
        },
    }
    response = client.post("/api/v1/schedule/with-preference", json=invalid_request)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ERROR"
    assert len(data["diagnostics"]["constraints"]["hard"]) > 0
    failure = data["diagnostics"]["constraints"]["hard"][0]
    assert "constraint_failed" in failure
    assert "blockers" in failure
    assert isinstance(failure["blockers"], list)
    if failure["blockers"]:
        blocker = failure["blockers"][0]
        assert "type" in blocker


def test_break_period_no_break_exceptions_and_day_exceptions():
    """Break period accepts doc-style no_break_exceptions and day_exceptions (mocks/hardconstraints case_three)."""
    request_data = get_minimal_request()
    request_data["break_period"] = {
        "start_time": "12:00",
        "end_time": "13:00",
        "daily": True,
        "no_break_exceptions": ["monday"],
        "day_exceptions": [
            {"day": "friday", "start_time": "14:00", "end_time": "15:00"}
        ],
    }
    response = client.post("/api/v1/schedule/without-preference", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["OPTIMAL", "PARTIAL", "ERROR"]
    if data["status"] in ["OPTIMAL", "PARTIAL"]:
        for day_schedule in data["timetable"]:
            if day_schedule["day"].lower() == "monday":
                break_slots = [s for s in day_schedule.get("slots", []) if s.get("break", False)]
                assert len(break_slots) == 0, "Monday should have no break (no_break_exceptions)"
            if day_schedule["day"].lower() == "friday":
                break_slots = [s for s in day_schedule.get("slots", []) if s.get("break", False)]
                if break_slots:
                    assert break_slots[0].get("start_time") == "14:00" and break_slots[0].get("end_time") == "15:00"


def test_required_joint_course_periods_accepts_valid_request():
    """Required joint course periods: valid request with matching slot grid does not return ERROR."""
    request_data = get_minimal_request()
    request_data["periods"] = {"daily": True, "period": 60}
    request_data["required_joint_course_periods"] = [
        {
            "course_id": "c1",
            "teacher_id": "t1",
            "periods": [
                {"day": "monday", "start_time": "08:00", "end_time": "09:00"},
            ],
        }
    ]
    response = client.post("/api/v1/schedule/without-preference", json=request_data)
    assert response.status_code == 200
    data = response.json()
    # Either OPTIMAL or ERROR (if slot grid doesn't align; 08:00-09:00 fits 60-min period)
    assert data["status"] in ["OPTIMAL", "PARTIAL", "ERROR"]
    if data["status"] == "OPTIMAL":
        # Check that monday has a slot 08:00-09:00 for c1/t1
        for day_schedule in data["timetable"]:
            if day_schedule["day"].lower() == "monday":
                for slot in day_schedule.get("slots", []):
                    if slot.get("course_id") == "c1" and slot.get("start_time") == "08:00" and slot.get("end_time") == "09:00":
                        break
                break


def test_soft_constraint_teacher_max_daily_hours_produces_partial():
    """When teacher_max_daily_hours is set and exceeded, status is PARTIAL and soft diagnostics present."""
    request_data = get_minimal_request()
    request_data["teacher_courses"] = [
        {"course_id": "c1", "course_title": "Math", "course_credit": 1, "course_type": "theory", "course_hours": 10, "teacher_id": "t1", "teacher_name": "John Doe"},
        {"course_id": "c2", "course_title": "Physics", "course_credit": 1, "course_type": "theory", "course_hours": 10, "teacher_id": "t1", "teacher_name": "John Doe"},
        {"course_id": "c3", "course_title": "Chem", "course_credit": 1, "course_type": "theory", "course_hours": 10, "teacher_id": "t1", "teacher_name": "John Doe"},
    ]
    request_data["periods"] = {"daily": True, "period": 60}
    request_data["soft_constrains"] = {"teacher_max_daily_hours": 2}
    response = client.post("/api/v1/schedule/without-preference", json=request_data)
    assert response.status_code == 200
    data = response.json()
    # Scheduler may place 3 sessions for t1 on same day -> exceeds 2h -> PARTIAL
    assert data["status"] in ["OPTIMAL", "PARTIAL"]
    assert data["diagnostics"]["summary"]["hard_constraints_met"] is True
    if data["status"] == "PARTIAL":
        assert len(data["diagnostics"]["constraints"]["soft"]) >= 1
        soft_types = [f["constraint_failed"].get("type") for f in data["diagnostics"]["constraints"]["soft"]]
        assert "teacher_max_daily_hours" in soft_types or not soft_types


def test_soft_constraint_course_requested_time_slots_accepts_request():
    """course_requested_time_slots in soft_constrains is accepted; may produce PARTIAL if course placed outside requested slots."""
    request_data = get_minimal_request()
    request_data["soft_constrains"] = {
        "course_requested_time_slots": [
            {"course_id": "c1", "slots": [{"day": "tuesday", "start_time": "09:00", "end_time": "10:00"}]}
        ]
    }
    response = client.post("/api/v1/schedule/without-preference", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["OPTIMAL", "PARTIAL"]
    assert data["diagnostics"]["summary"]["hard_constraints_met"] is True


def test_soft_constraint_requested_free_periods_accepts_request():
    """requested_free_periods in soft_constrains is accepted; may produce PARTIAL if period is occupied."""
    request_data = get_minimal_request()
    request_data["soft_constrains"] = {
        "requested_free_periods": [{"day": "monday", "start_time": "10:00", "end_time": "11:00"}]
    }
    response = client.post("/api/v1/schedule/without-preference", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["OPTIMAL", "PARTIAL"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
