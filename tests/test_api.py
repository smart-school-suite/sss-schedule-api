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
    
    # Should have a status
    assert "status" in data
    assert data["status"] in ["OPTIMAL", "FEASIBLE", "INFEASIBLE", "ERROR"]


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
    assert data["status"] == "INFEASIBLE" or len(data["messages"]["error_message"]) > 0


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
    if data["status"] in ["OPTIMAL", "FEASIBLE"]:
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
    if data["status"] in ["OPTIMAL", "FEASIBLE"]:
        for day_schedule in data["timetable"]:
            if day_schedule["day"].lower() == "monday":
                for slot in day_schedule.get("slots", []):
                    if not slot.get("break", False):
                        # Should not overlap with 14:00-17:00
                        start = slot.get("start_time", "")
                        # Basic check (more robust parsing would be better)
                        assert not (start >= "14:00" and start < "17:00")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
