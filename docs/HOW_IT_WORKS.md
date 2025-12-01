# How the OR-Tools Scheduling Solver Works

## Overview

The solver uses **Constraint Programming (CP-SAT)** from Google OR-Tools to find optimal timetables. Think of it as a sudoku solver but for school schedules.

---

## The Core Concept

### 1. **Problem Definition**

We have:
- **Teachers** who need to teach courses
- **Courses** that need a certain number of hours per week
- **Halls** (classrooms) where courses happen
- **Time slots** (e.g., Monday 8:00-9:00, Monday 9:00-10:00, etc.)

We need to answer: **"Which course happens in which hall at which time?"**

### 2. **Decision Variables (The Unknown)**

The solver creates **boolean variables** (0 or 1):

```python
x[course, day, slot, hall] = 1  # If course is scheduled here
x[course, day, slot, hall] = 0  # If not scheduled here
```

For example:
- `x[Math101, Monday, 8:00, RoomA] = 1` means "Math 101 is taught on Monday at 8:00 in Room A"
- `x[Math101, Monday, 8:00, RoomB] = 0` means "Math 101 is NOT in Room B at that time"

### 3. **Constraints (The Rules)**

We tell the solver what's allowed and what's not:

#### Hard Constraints (MUST be satisfied):
```python
# 1. No teacher double-booking
# A teacher can't teach two courses at the same time
For each (day, slot):
    Sum of all courses for teacher T at (day, slot) <= 1

# 2. No hall double-booking  
# A hall can't host two courses at the same time
For each (day, slot):
    Sum of all courses in hall H at (day, slot) <= 1

# 3. Course frequency
# If a course needs 3 hours/week, schedule exactly 3 slots
For each course C:
    Sum of all x[C, day, slot, hall] = required_hours

# 4. Teacher busy periods
# Don't schedule when teacher is unavailable
If teacher busy on Monday 2pm-4pm:
    x[any_course_by_that_teacher, Monday, 2pm-4pm, any_hall] = 0

# 5. Break periods
# No classes during lunch break
For lunch 12:00-13:00:
    All x[any_course, any_day, 12:00-13:00, any_hall] = 0

# 6. Course type matches hall type
# Practical courses need labs, theory courses need lecture halls
If course is practical:
    Only allow x[course, day, slot, lab_halls]
```

### 4. **Solving**

The solver tries **billions of combinations** in milliseconds using advanced algorithms:
- It uses **backtracking** (tries possibilities, backtracks if rules violated)
- **Constraint propagation** (eliminates impossible options early)
- **Branch and bound** (focuses on promising solutions)

When it finds a combination where ALL constraints are satisfied, it returns that as the schedule.

---

## Step-by-Step Example

### Input:
```json
{
  "teachers": [{"teacher_id": "T1", "name": "Dr. Smith"}],
  "teacher_courses": [{
    "course_id": "MATH101",
    "course_title": "Calculus",
    "teacher_id": "T1",
    "course_hours": 90  // 90 minutes per week
  }],
  "halls": [{"hall_id": "R1", "hall_name": "Room 1", "hall_type": "lecture"}],
  "operational_period": {
    "start_time": "08:00",
    "end_time": "12:00",
    "days": ["monday", "wednesday"]
  }
}
```

### What the Solver Does:

**Step 1: Discretize Time**
```
Monday:    [08:00-08:30, 08:30-09:00, 09:00-09:30, ..., 11:30-12:00]
Wednesday: [08:00-08:30, 08:30-09:00, 09:00-09:30, ..., 11:30-12:00]
Total: 16 slots (8 per day)
```

**Step 2: Calculate Sessions Needed**
```
Course needs 90 minutes
Each slot = 30 minutes
Sessions needed = 90 / 30 = 3 sessions
```

**Step 3: Create Variables**
```python
# For each possible scheduling combination:
x[MATH101, Monday, 08:00, R1] = ?
x[MATH101, Monday, 08:30, R1] = ?
x[MATH101, Monday, 09:00, R1] = ?
... (16 variables total for this simple case)
```

**Step 4: Apply Constraints**
```python
# Constraint: Exactly 3 sessions
x[MATH101, Mon, 08:00, R1] + x[MATH101, Mon, 08:30, R1] + ... = 3

# Constraint: No double booking (already satisfied since only 1 course)
# Constraint: Teacher T1 can't be in two places at once (already satisfied)
```

**Step 5: Solve**
```
Solver finds: 
x[MATH101, Monday, 08:00, R1] = 1  ✓
x[MATH101, Monday, 08:30, R1] = 1  ✓
x[MATH101, Monday, 09:00, R1] = 1  ✓
All others = 0

Total = 3 sessions ✓ Constraint satisfied!
```

**Step 6: Format Output**
```json
{
  "timetable": [
    {
      "day": "monday",
      "slots": [
        {
          "start_time": "08:00",
          "end_time": "09:30",
          "teacher_name": "Dr. Smith",
          "course_name": "Calculus",
          "hall_name": "Room 1",
          "duration": "1h 30min",
          "break": false
        }
      ]
    }
  ],
  "status": "OPTIMAL"
}
```

---

## How Constraints Are Modeled in OR-Tools

### Example 1: Teacher Can't Be in Two Places

```python
# For Teacher T1 on Monday at 8:00
courses_taught_by_T1 = [MATH101, PHYS101, CHEM101]

# Sum of all courses by T1 at Monday 8:00 across all halls <= 1
model.Add(
    sum(x[MATH101, Monday, 8:00, hall] for hall in all_halls) +
    sum(x[PHYS101, Monday, 8:00, hall] for hall in all_halls) +
    sum(x[CHEM101, Monday, 8:00, hall] for hall in all_halls)
    <= 1
)
```

### Example 2: Course Needs Exactly 3 Sessions

```python
# MATH101 needs exactly 3 one-hour sessions
model.Add(
    sum(x[MATH101, day, slot, hall] 
        for day in all_days 
        for slot in all_slots 
        for hall in all_halls) 
    == 3
)
```

### Example 3: Lunch Break (No Classes)

```python
# Between 12:00-13:00, all variables must be 0
for course in all_courses:
    for day in all_days:
        for hall in all_halls:
            model.Add(x[course, day, lunch_slot, hall] == 0)
```

---

## Why This Approach Works

### Advantages:
1. **Guaranteed Correctness**: If a solution exists, OR-Tools will find it
2. **Fast**: Can handle 20 teachers, 50 courses in ~5 seconds
3. **Optimal**: Can optimize for preferences (minimize gaps, balance workload)
4. **Flexible**: Easy to add new constraints
5. **Deterministic**: Same input always gives same output

### Limitations:
1. **INFEASIBLE if impossible**: If constraints conflict, no solution exists
2. **Exponential growth**: 100+ teachers may be slow without tuning
3. **Requires careful modeling**: Constraints must be correctly formulated

---

## Testing with Postman

### Step 1: Start the Server

```bash
cd /home/nyuydine/Documents/smartschools/sss-schedule-api
make run
# or
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

Server should say: `Uvicorn running on http://0.0.0.0:8080`

### Step 2: Open Postman

1. Create a new **POST** request
2. URL: `http://localhost:8080/api/v1/schedule/without-preference`

### Step 3: Set Headers

In the **Headers** tab:
```
Key: Content-Type
Value: application/json
```

### Step 4: Add Request Body

In the **Body** tab, select **raw** and **JSON**, then paste:

```json
{
  "teachers": [
    {
      "teacher_id": "T1",
      "name": "Dr. Alice Smith"
    },
    {
      "teacher_id": "T2",
      "name": "Prof. Bob Johnson"
    }
  ],
  "teacher_courses": [
    {
      "course_id": "MATH101",
      "course_title": "Calculus I",
      "course_credit": 3,
      "course_type": "theory",
      "course_hours": 90,
      "teacher_id": "T1",
      "teacher_name": "Dr. Alice Smith"
    },
    {
      "course_id": "PHYS201",
      "course_title": "Physics Lab",
      "course_credit": 4,
      "course_type": "practical",
      "course_hours": 120,
      "teacher_id": "T2",
      "teacher_name": "Prof. Bob Johnson"
    }
  ],
  "halls": [
    {
      "hall_id": "R101",
      "hall_name": "Lecture Hall A",
      "hall_capacity": 50,
      "hall_type": "lecture"
    },
    {
      "hall_id": "LAB1",
      "hall_name": "Physics Lab 1",
      "hall_capacity": 30,
      "hall_type": "lab"
    }
  ],
  "teacher_busy_period": [
    {
      "teacher_id": "T1",
      "teacher_name": "Dr. Alice Smith",
      "day": "monday",
      "start_time": "15:00",
      "end_time": "17:00"
    }
  ],
  "teacher_prefered_teaching_period": [],
  "hall_busy_periods": [],
  "break_period": {
    "start_time": "12:00",
    "end_time": "13:00",
    "daily": true
  },
  "operational_period": {
    "start_time": "08:00",
    "end_time": "17:00",
    "daily": true,
    "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
    "constrains": []
  },
  "soft_constrains": {}
}
```

### Step 5: Send Request

Click **Send**

### Expected Response:

```json
{
  "timetable": [
    {
      "day": "monday",
      "slots": [
        {
          "day": "monday",
          "start_time": "08:00",
          "end_time": "09:30",
          "teacher_id": "T1",
          "teacher_name": "Dr. Alice Smith",
          "course_id": "MATH101",
          "course_name": "Calculus I",
          "hall_id": "R101",
          "hall_name": "Lecture Hall A",
          "break": false,
          "duration": "1h 30min"
        },
        {
          "day": "monday",
          "start_time": "12:00",
          "end_time": "13:00",
          "break": true
        }
      ]
    },
    {
      "day": "tuesday",
      "slots": [
        {
          "day": "tuesday",
          "start_time": "08:00",
          "end_time": "10:00",
          "teacher_id": "T2",
          "teacher_name": "Prof. Bob Johnson",
          "course_id": "PHYS201",
          "course_name": "Physics Lab",
          "hall_id": "LAB1",
          "hall_name": "Physics Lab 1",
          "break": false,
          "duration": "2h 0min"
        }
      ]
    }
  ],
  "messages": {
    "error_message": [],
    "success_message": []
  },
  "status": "OPTIMAL",
  "solve_time_seconds": 0.123
}
```

---

## Test Scenarios in Postman

### Test 1: Simple Schedule (should work)
- 1 teacher, 1 course, 1 hall
- Should return OPTIMAL with schedule

### Test 2: Conflict Test (should fail gracefully)
- 1 teacher, 2 courses at same time
- 1 hall only
- Should return INFEASIBLE or error message

### Test 3: Teacher Busy Period
- Add busy period Monday 14:00-17:00
- Verify no classes scheduled during that time

### Test 4: Course Type Matching
- Add practical course
- Only provide lecture hall (no lab)
- Should return INFEASIBLE or skip that course

### Test 5: With Preferences
Change URL to: `http://localhost:8080/api/v1/schedule/with-preference`

Add to body:
```json
"teacher_prefered_teaching_period": [
  {
    "teacher_id": "T1",
    "teacher_name": "Dr. Alice Smith",
    "day": "tuesday",
    "start_time": "09:00",
    "end_time": "11:00"
  }
]
```

Should try to schedule Dr. Smith's classes on Tuesday 9-11am.

---

## Troubleshooting

### Problem: Connection refused
**Solution:** Make sure server is running (`make run`)

### Problem: 422 Validation Error
**Solution:** Check JSON format matches schema exactly:
- Use `"day"` not `"day_of_week"`
- All required fields present
- Times in HH:MM format

### Problem: Status = INFEASIBLE
**Solution:** 
- Check if constraints conflict
- Reduce course hours
- Add more halls or time slots
- Remove busy periods

### Problem: Empty timetable
**Solution:**
- Increase operational hours
- Check if course_hours matches available time
- Verify hall types match course types

---

## Key Takeaways

1. **OR-Tools finds optimal solutions** by trying combinations intelligently
2. **Constraints define what's valid** (teacher availability, hall capacity, etc.)
3. **Boolean variables represent decisions** (schedule here? yes/no)
4. **Fast and deterministic** - same input = same output
5. **Test with Postman** using POST requests with JSON body

The solver is like a super-smart assistant that considers all rules simultaneously and finds a perfect arrangement (or tells you it's impossible).

