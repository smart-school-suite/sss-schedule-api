# Scheduling API – Feedback & Improvement Tracker

Based on: *Scheduling API Improvement And Expectation (1) (1).pdf*

---

## 1. Daily Schedule Distribution

| Item | Feedback | Action |
|------|----------|--------|
| **Observed** | On some days no classes after break even when no conflicts. | |
| **Expected** | Distribute classes sequentially within operational hours; fill slots from start to end; continue after break when sessions remain and no constraint blocks. | **Solver:** Prefer/encourage placing sessions in earlier slots and after-break slots so the day is filled; avoid leaving post-break slots empty when work remains. **Done:** In `_add_soft_constraints_and_objective`: (1) `_get_break_end_for_day` / `_is_slot_after_break` helpers; (2) objective term per assignment: earlier slots get higher weight `(max_slots - slot_idx)`; (3) bonus +1 for each assignment in a post-break slot. |

---

## 2. Operational Period Constraint Enforcement

| Item | Feedback | Action |
|------|----------|--------|
| **Observed** | Only Monday and Saturday used despite Mon–Sat operational. | |
| **Expected** | Schedule across **all** operational days when sessions remain and no constraint prevents it. | **Solver:** Spread assignments across all operational days (e.g. balance or sequential day usage) so no operational day is skipped unless necessary. **Done:** Objective term in `_add_soft_constraints_and_objective`: per-day indicator `day_has_class[day]` with weight 2; maximize so solver prefers using more operational days. |

---

## 3. Required Joint Course Periods Enforcement

| Item | Feedback | Action |
|------|----------|--------|
| **Observed** | required_joint_course_periods not enforced; scheduler didn’t fail when violated. | |
| **Expected** | **Hard constraint:** Course must be scheduled exactly at the given day and time. If teacher_id/hall_id not in request lists, still enforce day+time with valid teacher/hall. If cannot enforce → **fail scheduling entirely**. | **Revert/change:** (1) Stop filtering out required joint entries that don’t match teacher_courses if we should instead “use available valid resources” for day+time. (2) Restore **fail** when a required joint period has no matching slot (do not skip silently). (3) When slot exists, **fix** the assignment for that course at that day/slot (and optional hall_id if valid). |

---

## 4. Requested Free Periods

| Item | Feedback | Action |
|------|----------|--------|
| **Observed** | Not enforced; no diagnostics when not satisfied; invalid entries (e.g. only `end_time`) accepted. | |
| **Expected** | Soft: try to satisfy; if not, **diagnostics** explaining why. **Validation:** Reject partial windows (e.g. only end_time; or day + only one of start/end). Support: day-only, time-only, day+time with clear semantics and diagnostics. | **Validation:** Reject `requested_free_periods` entries with only `end_time` or only `start_time` (and day+one time field). **Solver:** Implement/improve requested free period logic; emit soft diagnostics when not satisfiable. **Done:** `_check_requested_free_periods` emits `requested_free_period` failure with `reason`, `occupied_by_course` in details. |

---

## 5. Teacher Requested Time Windows

| Item | Feedback | Action |
|------|----------|--------|
| **Observed** | Not enforced; no diagnostics; invalid windows (day-only, time-only) accepted. | |
| **Expected** | Soft: try to place teacher’s sessions in requested windows; if not, **diagnostics** per window. **Validation:** day ⇒ need start_time+end_time; start_time or end_time ⇒ need the other; reject day-only and time-only unless explicitly supported. | **Validation:** Validate `teacher_requested_time_windows` (and backend alias): complete window = (day + start_time + end_time) or define and support day-only/time-only explicitly. **Solver:** Honor windows when feasible; add diagnostics when not. **Done:** `_check_requested_time_windows_and_assignments` emits `teacher_requested_time_windows` failure with `reason`, `scheduled_at`; supports `windows` and `requested_time_windows`. |

---

## 6. Hall Requested Time Windows

| Item | Feedback | Action |
|------|----------|--------|
| **Observed** | Not enforced; no diagnostics; invalid windows accepted. | |
| **Expected** | Same as teacher: soft preference, diagnostics when not satisfied; validate complete windows (day + start_time + end_time) or define partial forms. | **Validation:** Same rules as teacher windows for `hall_requested_time_windows`. **Solver:** Prefer placing activities in hall within requested windows; diagnostics when not. **Done:** Emits `hall_requested_time_windows` failure with `reason`, `scheduled_at`; supports `windows` and `requested_time_windows`. |

---

## 7. Requested Assignments

| Item | Feedback | Action |
|------|----------|--------|
| **Observed** | Not enforced; no diagnostics; invalid entries (missing day or time, partial placement) accepted. | |
| **Expected** | Soft: try to place (course_id, teacher_id, hall_id) at requested day and start_time–end_time; if not, **diagnostics**. **Validation:** course_id, teacher_id, hall_id required; complete placement (day + start_time + end_time) or explicitly defined partial; reject partial otherwise. | **Validation:** Require course_id, teacher_id, hall_id; require full placement (day + start_time + end_time) or document partial. **Solver:** Already has some logic; ensure diagnostics when requested assignment not satisfied. **Done:** Emits `requested_assignments` failure with `reason` in details when not satisfied. |

---

## 8. Course Requested Time Slots

| Item | Feedback | Action |
|------|----------|--------|
| **Observed** | Not enforced; no diagnostics; invalid slots (day-only, time-only, only end_time) accepted. | |
| **Expected** | Soft: try to place course in requested slots; if not, **diagnostics**. **Validation:** Reject partial (only end_time or only start_time); reject day without time and time without day unless supported. | **Validation:** Validate `course_requested_time_slots` entries: complete slot or defined partial. **Solver:** Prefer requested slots; emit diagnostics when not satisfied. **Done:** Emits `course_requested_time_slots` failure with `reason`, `scheduled_at`; supports `slots` and `requested_time_slots`. |

---

## 9. Teacher Preference Endpoint Validation

| Item | Feedback | Action |
|------|----------|--------|
| **Observed** | With-preference endpoint runs even when teacher_preference is missing/empty. | |
| **Expected** | With-preference endpoint must **require** teacher preference data; if missing or empty → **validation error**, do not run scheduling. | **Router/schema:** For `/schedule/with-preference`, require non-empty `teacher_preferred_periods` (backend) or `teacher_prefered_teaching_period` (legacy); return 422 if missing or empty. **Done:** `validate_teacher_preference_required` in `service/validation.py`; router returns 422 with `errors.teacher_prefered_teaching_period` when empty. |

---

## Implementation priority (suggested)

1. **Validation (all soft/preference inputs)** – Reject invalid requested_free_periods, teacher/hall requested time windows, requested_assignments, course_requested_time_slots; and require teacher preference on with-preference endpoint.
2. **Required joint periods** – Restore strict hard constraint: fail when a required joint period (that matches teacher_courses) has no slot or cannot be placed; enforce placement when slot exists.
3. **Operational day distribution** – Solver: spread sessions across all operational days when possible.
4. **Daily schedule distribution** – Solver: fill slots through the day including after break when work remains.
5. **Soft constraints + diagnostics** – Ensure requested free periods, teacher/hall windows, requested assignments, and course requested slots all produce clear diagnostics when not satisfied.

---

## File references

- **Solver:** `service/ortools_solver.py` (constraints, objectives, slot building, diagnostics).
- **Schemas/validation:** `models/schemas.py` (BackendScheduleRequest, SoftConstraints, request bodies).
- **Router:** `routers/schedule.py` (with-preference vs without-preference; validation before solve).
- **Backend converter:** `backend_request_to_scheduling_request()` in `models/schemas.py`.

---

## Implementation summary

A standalone summary of what was implemented (phases, files, and how to verify) is in **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)**.

For **mocks vs implemented constraints** and **how to add or change constraints without breaking the response**, see **[MOCKS_AND_CONSTRAINTS.md](MOCKS_AND_CONSTRAINTS.md)**.
