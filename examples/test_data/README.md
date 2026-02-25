# Test data format (backend request format)

The JSON files in this folder match the **backend request format** that the schedule API accepts. The API accepts this format and converts it internally to the solver format.

- **Endpoint:** `POST /api/v1/schedule/with-preference` or `POST /api/v1/schedule/without-preference`
- **Schema:** `BackendScheduleRequest` in `models/schemas.py` (teachers[].teacher_name, teacher_courses[].course_name, course_type as list, halls[].hall_type as list, hard_constraints, soft_constraints).
- The API also accepts the **legacy** flat format (break_period/operational_period at top level, teachers[].name, etc.) by detecting the absence of `hard_constraints`.

## Backend format (accepted by API)

| Field | Backend format |
|--------|----------------|
| **Teachers** | `teachers[]` with `teacher_id`, `teacher_name` |
| **Teacher preferences** | `teacher_preferred_periods` (optional): `teacher_id`, `day`, `start_time`, `end_time` |
| **Teacher busy** | `teacher_busy_periods`: `teacher_id`, `day`, `start_time`, `end_time` |
| **Teacher courses** | `teacher_courses[]`: `teacher_id`, `course_id`, `course_name`, `course_type` as list (e.g. `["Theoritical","Practical"]`); `course_credit`/`course_hours` optional (default 1 and 30) |
| **Halls** | `halls[]`: `hall_id`, `hall_name`, `hall_capacity`, `hall_type` as list (e.g. `["Lecture Hall","Practical"]`) |
| **Hard constraints** | `hard_constraints`: `operational_period` (with `operational_days`, `day_exceptions`), `break_period` (with `day_exceptions`, `no_break_exceptions`), `schedule_period_duration_minutes`, `required_joint_course_periods` |
| **Soft constraints** | `soft_constraints` (same structure as `SoftConstraints`) |

## Notes

- The API converts backend format to the internal solver format automatically (`backend_request_to_scheduling_request` in `models/schemas.py`). Course type list is mapped (first item: "Theoritical"→"theory", "Practical"→"practical"); hall type list is mapped (first match: "Lecture Hall"/"lecture"→"lecture", "Practical"/"lab"→"lab").
- **required_joint_course_periods:** In these test files, many entries reference `course_id`/`teacher_id` that are not in `teacher_courses`. The solver will return ERROR for those ("course_id and teacher_id do not match any teacher_courses entry"). For a feasible schedule, only include required joint periods that match an existing teacher_courses row.

## How to use this data

- Send the JSON as-is to `POST /api/v1/schedule/with-preference` or `POST /api/v1/schedule/without-preference` with `Content-Type: application/json`. The API accepts this backend format.
- Validate that a file matches the schema: `python examples/test_data/validate_test_data.py` (uses `BackendScheduleRequest`).

## Validate test data against the API schema

From the repo root:

```bash
python examples/test_data/validate_test_data.py
```

This loads each JSON file with the same Pydantic model as the API and prints the first error (field name, type, or structure). Fix the reported issues in order.

## Reference

- **Backend request schema:** `models/schemas.py` – `BackendScheduleRequest`, `BackendTeacher`, `BackendTeacherCourse`, `BackendHall`, `BackendHardConstraints`, etc.
- **Legacy format** (still accepted if body has no `hard_constraints`): `examples/sample_request.json`, `mocks/requests/minimal_valid.json`.
