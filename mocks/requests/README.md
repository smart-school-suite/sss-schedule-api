# Ready-to-use request bodies (from mocks)

Use these JSON files to test the API in **Swagger** or with **curl**. They are built from `mocks/constraints/hardconstraints.json` and `mocks/constraints/softconstraints.json`.

## How to use in Swagger

1. Start the server: `uvicorn main:app --reload --port 8080`
2. Open **http://localhost:8080/docs**
3. Expand **POST /api/v1/schedule/without-preference** (or **with-preference**)
4. Click **Try it out**
5. Open one of the JSON files below, copy its contents, and paste into the **Request body**
6. Click **Execute**

## Files

| File | Description |
|------|-------------|
| `break_period_mock.json` | Break period from hardconstraints **case_three**: `no_break_exceptions: ["monday"]`, `day_exceptions` for Friday |
| `required_joint_periods_mock.json` | **required_joint_course_periods** from hardconstraints: locked course at Monday 10:00–11:00 and Wednesday 14:00–15:00 |
| `soft_constraints_mock.json` | Soft constraints from softconstraints: `teacher_max_daily_hours`, `course_requested_time_slots`, `requested_free_periods` |
| `minimal_valid.json` | Minimal valid request (no optional constraints) |

## curl examples

```bash
# Minimal
curl -X POST http://localhost:8080/api/v1/schedule/without-preference \
  -H "Content-Type: application/json" \
  -d @mocks/requests/minimal_valid.json

# With break period mock
curl -X POST http://localhost:8080/api/v1/schedule/without-preference \
  -H "Content-Type: application/json" \
  -d @mocks/requests/break_period_mock.json

# With required joint periods
curl -X POST http://localhost:8080/api/v1/schedule/without-preference \
  -H "Content-Type: application/json" \
  -d @mocks/requests/required_joint_periods_mock.json

# With soft constraints
curl -X POST http://localhost:8080/api/v1/schedule/without-preference \
  -H "Content-Type: application/json" \
  -d @mocks/requests/soft_constraints_mock.json
```
