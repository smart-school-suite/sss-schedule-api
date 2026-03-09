# Mocks, Constraints, and Stable Response Shape

## Stable response shape (do not change)

The API **response shape is fixed** so clients can rely on it regardless of which constraints are added or changed:

- **`diagnostics.constraints.hard`** – `List[ConstraintFailure]`
- **`diagnostics.constraints.soft`** – `List[ConstraintFailure]`
- **`diagnostics.summary`** – `message`, `hard_constraints_met`, `soft_constraints_met`, `failed_soft_constraints_count`, `failed_hard_constraints_count`

Each **ConstraintFailure** has:

- **`constraint_failed`** – `{ "type": "<constraint_type>", "details": { ... } }` (and optionally `rule`, etc.)
- **`blockers`** – `List[DiagnosticBlocker]` where each has `type`, `entity`, `conflict`, `evidence`
- **`suggestions`** – `List[Dict]` (optional)

New or modified constraints **must not change this structure**. They only add or change entries in `hard`/`soft` and the contents of `details`/`blockers`/`suggestions` for that constraint type.

---

## Mocks vs implementation (checked)

The repo contains **mocks** under `mocks/violations/`, `mocks/diagnostics/`, `mocks/suggestion/`. They are **reference/examples**. Being present in mocks does **not** mean we must implement them exactly; if a mock assumes a different architecture or shape, we keep our stable response and document the mapping below.

### Mock violation files (shape: `type`, `entity`, `conflict`, `evidence`)

These use a **different** top-level shape than our API (we use `ConstraintFailure` with `constraint_failed`, `blockers`, `suggestions`). We map them to our **constraint types** and emit diagnostics in our **stable** form.

| Mock file | Our constraint type | Implemented? | Notes |
|-----------|---------------------|--------------|--------|
| `violations/course/RequiredJointCourseViolation.json` | `REQUIRED_JOINT_COURSE_PERIODS` (hard) | Yes | Emitted as hard failure with blockers e.g. NO_MATCHING_SLOT, HALL_UNAVAILABLE |
| `violations/course/CourseRequestedTimeSlotViolation.json` | `course_requested_time_slots` (soft) | Yes | Emitted as soft failure with COURSE_SCHEDULED_OUTSIDE_REQUESTED_SLOTS |
| `violations/course/CourseMaxDailyFrequencyViolation.json` | `course_max_daily_frequency` (soft) | Yes | Emitted as soft failure with MAX_COURSE_DAILY_FREQUENCY_EXCEEDED |
| `violations/schedule/RequestedFreePeriodViolation.json` | `requested_free_period` (soft) | Yes | Emitted as soft failure with REQUESTED_FREE_PERIOD_OCCUPIED |
| `violations/schedule/RequestedAssignmentViolation.json` | `requested_assignments` (soft) | Yes | Emitted as soft failure with REQUESTED_ASSIGNMENT_NOT_SATISFIED |
| `violations/schedule/BreakPeriodViolation.json` | break period (hard, slot feasibility) | Yes | Enforced in solver (no class in break); no separate diagnostic unless infeasible |
| `violations/schedule/MaxDailyPeriodViolation.json` | `schedule_max_periods_per_day` (soft) | Yes | Emitted as soft failure |
| `violations/schedule/MaxFreePeriodPerDayViolation.json` | `schedule_max_free_periods_per_day` (soft) | Yes | Emitted as soft failure |
| `violations/schedule/OperationalPeriodViolation.json` | operational period (hard) | Yes | Enforced via slot grid; no class outside operational hours |
| `violations/schedule/PeriodDurationViolation.json` | period duration (hard) | Yes | Enforced via slot building |
| `violations/teacher/TeacherMaxDailyHourViolation.json` | `teacher_max_daily_hours` (soft) | Yes | Emitted as soft failure |
| `violations/teacher/TeacherMaxWeeklyHourViolation.json` | `teacher_max_weekly_hours` (soft) | Yes | Emitted as soft failure |
| `violations/teacher/TeacherRequestedTimeSlotViolation.json` | `teacher_requested_time_windows` (soft) | Yes | Emitted as soft failure with TEACHER_SCHEDULED_OUTSIDE_REQUESTED_WINDOWS |
| `violations/teacher/TeacherBusyViolation.json` | teacher busy (hard) | Yes | Enforced in slot feasibility |
| `violations/teacher/TeacherUnavailable.json` | teacher availability | Part of validation / feasibility | No separate violation type |
| `violations/teacher/TeacherCourseViolation.json` | teacher_courses mismatch | Yes | Validation / required joint failure (TEACHER_COURSE_MISMATCH) |
| `violations/teacher/TeacherInsufficiency.json` | insufficient teachers | Infeasibility | Can surface as generic infeasible/ERROR |
| `violations/hall/HallBusy.json` | hall busy (hard) | Yes | Enforced in slot feasibility |
| `violations/hall/HallRequestedTimeSlotViolation.json` | `hall_requested_time_windows` (soft) | Yes | Emitted as soft failure with HALL_SCHEDULED_OUTSIDE_REQUESTED_WINDOWS |

### Diagnostics mocks (`mocks/diagnostics/`)

These are closer to our shape (`constraint_failed`, `blockers`, `suggestions`). We align with this **structure**; field names and IDs in mocks may differ. Our code emits the same **types** and structure so responses remain stable.

---

## Adding or modifying constraints (without breaking things)

1. **Response shape** – Do not change `ConstraintFailure`, `DiagnosticBlocker`, or the top-level `diagnostics.constraints.hard` / `soft` / `summary`. New constraints only add items to those lists with a new `constraint_failed.type` and appropriate `details`/`blockers`/`suggestions`.

2. **Hard constraints (affect feasibility)**  
   - If it’s a **fixed assignment** (e.g. required joint): add or extend logic in `_add_required_joint_period_constraints()` (or a similar dedicated step), and append to the **failures** list returned so the solver returns ERROR.  
   - If it’s a **slot rule** (break, operational, teacher/hall busy): enforce in `_is_slot_feasible()` or slot building so that no variable is created for invalid slots. Failures then surface as infeasibility or existing hard diagnostic paths.

3. **Soft constraints (post-solve checks)**  
   - Implement a method that takes the **timetable** (and request from `self.request`), computes violations, and appends **`ConstraintFailure`** instances to **`self._soft_failures`**.  
   - Register that method in the solver’s soft-check flow (see comment in `service/ortools_solver.py`: `_SOFT_CONSTRAINT_CHECK_METHODS` or the single place that calls the requested-time and free-period checks).  
   - Use a **new** `constraint_failed.type` (e.g. `"my_new_constraint"`) and put all variable data in `details` and `blockers` so the response shape stays the same.

4. **Validation (input)**  
   - If the new constraint has request input, add validation in `service/validation.py` and return 422 for invalid input so the solver never sees bad data.

5. **Mocks**  
   - You can add or update mocks under `mocks/violations/` or `mocks/diagnostics/` for documentation or tests. The API does **not** need to match every mock field-for-field; we keep the stable response shape and map mock “violation types” to our `constraint_failed.type` and blockers as above.

---

## Summary

- **Response shape is stable:** `diagnostics.constraints.hard` / `soft` as lists of `ConstraintFailure` with `constraint_failed`, `blockers`, `suggestions`. Do not break this.  
- **Mocks are checked** in the table above; we implement the behaviour and emit diagnostics in our format. Mocks that don’t match the architecture are not mandatory to replicate literally.  
- **To add or change constraints:** keep the same response structure; add hard logic in the right solver step, or a soft-check method that appends `ConstraintFailure`s; register the check; validate input in `validation.py` if needed.
