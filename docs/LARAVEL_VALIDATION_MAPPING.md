# Laravel validation ↔ Scheduling API mapping

This doc aligns **Laravel request validation** (`PreferenceRequestValidation.php`, `WithoutPreferenceRequestValidation.php`) with the **Scheduling API** request shape and validation. Use it so the payload Laravel sends matches what the API expects.

---

## 1. Request shape: two formats accepted by the API

The API accepts **one of two** JSON shapes:

| Format | When | Structure |
|--------|------|-----------|
| **Backend** | Body contains `"hard_constraints"` | Top-level: `teachers`, `teacher_courses`, `halls`, `teacher_preferred_periods` (with-preference), `teacher_busy_periods`, `hall_busy_periods`, `hard_constraints`, `soft_constraints`. |
| **Legacy** | Body has no `"hard_constraints"` | Top-level: `break_period`, `operational_period`, `periods`, `teachers`, `teacher_courses`, `halls`, `teacher_prefered_teaching_period`, etc. |

**Recommendation:** Have Laravel send the **backend** format so hard/soft constraints and operational settings are explicit. Build the payload like this:

- Put **operational_period**, **break_period**, **schedule_period_duration_minutes**, **required_joint_course_periods** inside **hard_constraints**.
- Put optional soft fields (e.g. **teacher_requested_time_windows**, **requested_free_periods**) inside **soft_constraints** (or leave **soft_constraints** empty / null).

---

## 2. Field name mapping (Laravel → Scheduling API)

Use these names in the JSON sent to the Scheduling API. Laravel can keep validating with their names internally, then map to these when building the request.

| Laravel validation key | Scheduling API expects | Notes |
|------------------------|-------------------------|--------|
| **Teachers** | | |
| `teachers.*.id` | `teacher_id` | API expects **teacher_id**, not **id**. |
| `teachers.*.teacher_name` | `teacher_name` | Same. |
| **Teacher preferred periods** (with-preference only) | | |
| `teacher_preferred_periods.*.teacher_id` | `teacher_id` | Same. |
| `teacher_preferred_periods.*.day` | `day` | Same; lowercase (monday, tuesday, …). |
| `teacher_preferred_periods.*.start_time` / `end_time` | `start_time`, `end_time` | Same; format `H:i` (e.g. 08:00). |
| **Teacher courses** | | |
| `teacher_courses.*.teacher_id`, `course_id`, `course_type` | Same | Same. |
| `teacher_courses.*.course_type.*` | `in: theoretical, practical` | API accepts theory/theoretical, practical; Laravel uses `theoretical,practical`. |
| **Halls** | | |
| `halls.*.hall_id` | `hall_id` | Same. |
| `halls.*.hall_name` | `hall_name` | Same. |
| `halls.*.capacity` | `hall_capacity` | API expects **hall_capacity**, not **capacity**. |
| `halls.*.type` | `hall_type` | API expects **hall_type**, and a **list** (e.g. `["Lecture Hall", "Practical"]`). Laravel uses **type**; map to **hall_type** when sending. |
| **Hard constraints** (nest under `hard_constraints`) | | |
| `operational_period.*` | `hard_constraints.operational_period` | Include **operational_days** (array of day names). |
| `break_period.*` | `hard_constraints.break_period` | Same structure. |
| `schedule_period_duration_minutes.*` | `hard_constraints.schedule_period_duration_minutes` | **duration_minutes** required. |
| — | `hard_constraints.required_joint_course_periods` | Array of `{ course_id, teacher_id, periods: [{ day, start_time, end_time, hall_id? }] }`. **course_id** and **teacher_id** must exist in **teacher_courses** in the same request. |
| **Soft constraints** (nest under `soft_constraints`) | | |
| `teacher_requested_time_windows.*.time_windows` | `windows` or `requested_time_windows` or `time_windows` | API accepts **windows** or **requested_time_windows**; it also accepts **time_windows** for compatibility. Each window: **day**, **start_time**, **end_time**. |
| `hall_requested_time_windows.*.windows` | `windows` or `requested_time_windows` or `time_windows` | Same as above. |
| `course_requested_time_slots.*.slots` | `slots` or `requested_time_slots` | Same. Each slot: **day**, **start_time**, **end_time**. |
| `requested_assignments.*` | Same keys | **course_id**, **teacher_id**, **hall_id** required; **day**, **start_time**, **end_time** optional; if one of day/start/end is set, all three required. |
| `requested_free_periods.*` | Same | If **day** or time given: **start_time** and **end_time** both required. |
| **Teacher / schedule limits** | | |
| `teacher_max_daily_hours.max_hours` | `soft_constraints.teacher_max_daily_hours` | API accepts number or `{ max_hours, teacher_exceptions }`. Laravel uses **max_hours**; API also accepts **max_daily_hours** in some shapes. |
| `teacher_max_weekly_hours.max_hours` | `soft_constraints.teacher_max_weekly_hours` | Same idea. |
| `schedule_max_periods_per_day.max_periods` | `soft_constraints.schedule_max_periods_per_day` | |
| `schedule_max_free_periods_per_day.max_free_periods` | `soft_constraints.schedule_max_free_periods_per_day` | |
| `course_max_daily_frequency.max_frequency` | `soft_constraints.course_max_daily_frequency` | |

---

## 3. Differences to fix on the Laravel side (when building the API request)

1. **teachers**  
   Send **teacher_id** (not **id**) for each teacher.

2. **halls**  
   Send **hall_capacity** (not **capacity**) and **hall_type** (not **type**); **hall_type** must be an array of strings.

3. **Payload structure**  
   - Nest **operational_period**, **break_period**, **schedule_period_duration_minutes**, **required_joint_course_periods** under **hard_constraints**.  
   - Put soft fields (e.g. **teacher_requested_time_windows**, **requested_free_periods**, **teacher_max_daily_hours**, …) under **soft_constraints** (one object).  
   - Keep **teachers**, **teacher_courses**, **halls**, **teacher_preferred_periods** (with-preference), **teacher_busy_periods**, **hall_busy_periods** at top level.

4. **required_joint_course_periods**  
   Every entry must use **course_id** and **teacher_id** that appear together in **teacher_courses** in the same request, and **hall_id** (if present) from **halls**. Validate this in Laravel before calling the API to avoid ERROR responses.

5. **Teacher requested time windows**  
   Laravel validates **time_windows**. The Scheduling API accepts **windows**, **requested_time_windows**, or **time_windows** (see below). So you can keep sending **time_windows** and the API will accept it.

---

## 4. With-preference vs without-preference

| Endpoint | Laravel validation | API behaviour |
|----------|--------------------|----------------|
| **POST /api/v1/schedule/with-preference** | `PreferenceRequestValidation`: **teacher_preferred_periods** required, non-empty | **teacher_preferred_periods** (or legacy **teacher_prefered_teaching_period**) must be non-empty; otherwise 422. |
| **POST /api/v1/schedule/without-preference** | `WithoutPreferenceRequestValidation`: no teacher_preferred_periods | Same payload shape; preferences are ignored. |

---

## 5. Summary for Laravel dev

- **Validate** on your side with your current rules (including **id**, **capacity**, **type**, **time_windows**).
- **When building the JSON for the Scheduling API**:  
  - Use **teacher_id**, **hall_capacity**, **hall_type** (array).  
  - Nest hard constraints under **hard_constraints** and soft under **soft_constraints**.  
  - For teacher/hall requested windows you can send **time_windows**; the API accepts it.  
  - Ensure every **required_joint_course_periods** entry references (course_id, teacher_id) from **teacher_courses** and hall_id from **halls**.

This keeps Laravel validation as-is while the payload sent to the Scheduling API matches what the API expects.
