# Scheduling API – Feedback Implementation Summary

This document describes the changes implemented in response to **Scheduling API Improvement And Expectation (1) (1).pdf**. The work was done in phases: validation first, then hard constraints, then solver objectives, then soft-constraint diagnostics.

---

## Overview

| Area | Status | Main change |
|------|--------|-------------|
| Input validation (soft/preference) | Done | 422 on invalid or partial soft-constraint input; teacher preference required on with-preference |
| Required joint course periods | Done | Hard constraint: fail scheduling if a required period has no slot or no hall; fix assignment when slot exists |
| Operational day distribution | Done | Solver prefers solutions that use more operational days |
| Daily schedule distribution | Done | Solver prefers earlier slots and post-break slots |
| Soft constraint diagnostics | Done | Clear failure details and support for alternate request keys |

---

## 1. Input validation (pre-solve)

**Goal:** Reject invalid or incomplete soft/preference data before the solver runs; require teacher preference on the with-preference endpoint.

**Where:** `service/validation.py`, `routers/schedule.py`

- **`validate_soft_constraints_inputs(soft_constrains)`**  
  Returns a list of `(field_path, message)`. Validates:
  - **requested_free_periods:** Reject partial windows (only `start_time`, only `end_time`, or `day` with only one of start/end).
  - **teacher_requested_time_windows** / **hall_requested_time_windows:** Each window must have `day`, `start_time`, `end_time`. Accepts key `windows` or `requested_time_windows`.
  - **requested_assignments:** Require `course_id`, `teacher_id`, `hall_id`; if any of day/time is given, require full placement (day + start_time + end_time).
  - **course_requested_time_slots:** Each slot must have `day`, `start_time`, `end_time`. Accepts key `slots` or `requested_time_slots`.

- **`validate_teacher_preference_required(teacher_prefered_teaching_period)`**  
  Returns errors if the value is `None` or an empty list.

- **Router behaviour:**  
  - **With-preference:** Runs both validators; if any errors → **422** with body `{"errors": { field_path: [messages] }}`.  
  - **Without-preference:** Runs only soft-constraint validation; same 422 on invalid soft input.

---

## 2. Required joint course periods (hard constraint)

**Goal:** Treat required joint course periods as a strict hard constraint: fail scheduling if any required period cannot be placed; when a matching slot exists, fix the assignment (and prefer requested `hall_id` if valid).

**Where:** `service/ortools_solver.py` → `_add_required_joint_period_constraints()`

- **No matching slot:** If (day, start_time, end_time) has no slot in the grid (e.g. wrong duration or outside operational hours), the solver adds a `ConstraintFailure` with blocker type **NO_MATCHING_SLOT** and returns **ERROR** (no silent skip).
- **No assignment variables:** If the course has no assignment variables, adds a failure with blocker type **COURSE_NOT_SCHEDULABLE** and returns ERROR.
- **No feasible hall:** If the slot exists but no hall is feasible (teacher/hall busy or break), adds a failure with **HALL_UNAVAILABLE** and returns ERROR.
- **Placement:** When a feasible hall exists, the solver fixes the assignment (`var == 1`). If the period specifies `hall_id` and that hall is feasible, it is used; otherwise the first feasible hall is chosen.

**Tests:**  
- `test_required_joint_course_periods_accepts_valid_request` – valid request with matching slot.  
- `test_required_joint_course_periods_fails_when_no_matching_slot` – required period with no matching slot (e.g. 2h when slots are 1h) → ERROR and diagnostics with NO_MATCHING_SLOT.

---

## 3. Operational day distribution

**Goal:** Spread sessions across all operational days when possible, so operational days are not skipped unnecessarily.

**Where:** `service/ortools_solver.py` → `_add_soft_constraints_and_objective()`

- For each operational day, a Boolean indicator **`day_has_class[day]`** is created and linked so it is 1 when there is at least one class on that day.
- The objective includes **`2 * sum(day_has_class[day])`**, so the solver is encouraged to use more days.
- Teacher preference terms keep a higher weight (10), so preference still dominates; day spread acts as a tie-breaker.

---

## 4. Daily schedule distribution (fill day, use post-break)

**Goal:** Fill the day sequentially and use post-break slots when work remains (avoid leaving post-break empty when there are no conflicts).

**Where:** `service/ortools_solver.py` → `_add_soft_constraints_and_objective()`, plus helpers

- **Helpers:**  
  - **`_get_break_end_for_day(day)`** – returns break end time for the day, or `None` if no break.  
  - **`_is_slot_after_break(day, slot_idx)`** – true if the slot starts at or after break end.

- **Objective terms (integer weights):**  
  - **Earlier slots:** For each assignment variable, weight **`max_slots_per_day - slot_idx`** (minimum 1), so earlier slots are preferred and the day fills from the start.  
  - **Post-break slots:** For each assignment in a post-break slot, add **+1** so the solver prefers using post-break when sessions remain.

---

## 5. Soft constraint diagnostics

**Goal:** When soft constraints are not satisfied, return clear diagnostics (reason and context) and support both main and alternate request keys.

**Where:** `service/ortools_solver.py` → `_check_requested_free_periods()`, `_check_requested_time_windows_and_assignments()`

- **requested_free_periods**  
  If a requested free period is occupied by a class: append a soft failure with type **requested_free_period**, details including **reason** (“Requested free period was occupied by a scheduled class”) and **occupied_by_course**.

- **course_requested_time_slots**  
  If a course is scheduled outside its requested slots: append failure type **course_requested_time_slots** with **reason** (“Course was scheduled outside requested time slots”) and **scheduled_at** (day, start_time, end_time).  
  Request key: **`slots`** or **`requested_time_slots`**.

- **requested_assignments**  
  If a requested (course_id, teacher_id, hall_id, day, start_time, end_time) is not in the timetable: append failure type **requested_assignments** with **reason** (“Requested assignment (course, teacher, hall at day/time) was not satisfied in the timetable.”).

- **teacher_requested_time_windows**  
  If a teacher is scheduled outside their requested windows: append failure with **reason** (“Teacher was scheduled outside requested time windows”) and **scheduled_at**.  
  Request key: **`windows`** or **`requested_time_windows`**.

- **hall_requested_time_windows**  
  Same pattern as teacher, with **reason** (“Hall was scheduled outside requested time windows”) and **scheduled_at**.  
  Request key: **`windows`** or **`requested_time_windows`**.

All of these are appended to **`diagnostics.constraints.soft`** and contribute to **PARTIAL** status and **diagnostics.summary.soft_constraints_met** / **failed_soft_constraints_count**.

---

## File reference

| File | Role |
|------|------|
| `service/validation.py` | Soft-constraint and teacher-preference validation; used before solve |
| `routers/schedule.py` | Calls validators; returns 422 with `errors` when validation fails |
| `service/ortools_solver.py` | Required joint constraints, objective terms (days, earlier/post-break slots), post-solve soft checks and diagnostics |
| `models/schemas.py` | Request/response schemas; backend conversion (no change to required joint filtering in this work) |
| `tests/test_api.py` | Tests for 422 on invalid/empty input, required joint success/failure, and soft constraint acceptance |

---

## How to verify

- Run the API test suite:  
  `pytest tests/test_api.py -v`
- With-preference with empty `teacher_prefered_teaching_period` → 422 and `errors.teacher_prefered_teaching_period`.
- Invalid soft input (e.g. requested_free_periods with only `end_time`) → 422 and `errors` listing the field.
- Required joint period with no matching slot (e.g. 2h period with 1h slots) → 200, status ERROR, diagnostics with NO_MATCHING_SLOT.
- Valid requests that violate soft constraints (e.g. requested free period occupied) → 200, status PARTIAL, `diagnostics.constraints.soft` with the corresponding failure type and details.

---

## Mocks and extensibility

- **Response shape is stable:** `diagnostics.constraints.hard` / `soft` are always lists of `ConstraintFailure` (with `constraint_failed`, `blockers`, `suggestions`). New or changed constraints must not change this structure.
- **Mocks vs implementation:** Mock files under `mocks/violations/` and `mocks/diagnostics/` are reference/examples. A full mapping (which mock maps to which constraint type, and whether we implement it) is in **[MOCKS_AND_CONSTRAINTS.md](MOCKS_AND_CONSTRAINTS.md)**. We do not change the architecture to match every mock literally.
- **Adding a new constraint:** See MOCKS_AND_CONSTRAINTS.md. In short: (1) Keep the same response shape. (2) Hard constraints: add logic in the appropriate solver step and return failures so status becomes ERROR when needed. (3) Soft constraints: implement `_check_<name>(self, timetable)` that appends to `self._soft_failures`, and add `"_check_<name>"` to `_SOFT_CONSTRAINT_CHECK_METHODS` in `service/ortools_solver.py`.

---

*Summary generated from the feedback tracker and implementation in the codebase.*
