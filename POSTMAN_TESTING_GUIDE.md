# 🚀 Quick Testing Guide with Postman

## Setup (One-Time)

### 1. Start the Server
```bash
cd /home/nyuydine/Documents/smartschools/sss-schedule-api
make run
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8080
INFO:     Application startup complete.
```

### 2. Import Postman Collection

**Option A: Import from file**
1. Open Postman
2. Click **Import** (top left)
3. Select `postman_collection.json` from the project root
4. Click **Import**

**Option B: Manual setup**
Create requests as shown below.

---

## ✅ Test 1: Health Check (Simplest)

**Method:** GET  
**URL:** `http://localhost:8080/health`  
**Expected Response:**
```json
{
  "status": "healthy"
}
```

**What this tests:** Server is running

---

## ✅ Test 2: Simple Schedule (1 Teacher, 1 Course)

**Method:** POST  
**URL:** `http://localhost:8080/api/v1/schedule/without-preference`  
**Headers:**
```
Content-Type: application/json
```

**Body (JSON):**
```json
{
  "teachers": [
    {"teacher_id": "T1", "name": "Dr. John Smith"}
  ],
  "teacher_courses": [
    {
      "course_id": "MATH101",
      "course_title": "Calculus I",
      "course_credit": 3,
      "course_type": "theory",
      "course_hours": 90,
      "teacher_id": "T1",
      "teacher_name": "Dr. John Smith"
    }
  ],
  "halls": [
    {
      "hall_id": "R101",
      "hall_name": "Room 101",
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

**Expected Response:**
```json
{
  "timetable": [
    {
      "day": "monday",
      "slots": [
        {
          "start_time": "08:00",
          "end_time": "09:30",
          "teacher_name": "Dr. John Smith",
          "course_name": "Calculus I",
          "hall_name": "Room 101",
          "duration": "1h 30min",
          "break": false
        },
        {
          "start_time": "12:00",
          "end_time": "13:00",
          "break": true
        }
      ]
    }
  ],
  "status": "OPTIMAL",
  "solve_time_seconds": 0.05
}
```

**What this tests:**
- ✅ Basic scheduling works
- ✅ Course of 90 min gets 3 sessions of 30 min each
- ✅ Break periods are included
- ✅ Response format is correct

---

## ✅ Test 3: With Teacher Preferences

**Method:** POST  
**URL:** `http://localhost:8080/api/v1/schedule/with-preference` ⬅️ **Note: with-preference**  
**Body:** Same as Test 2, but add:

```json
{
  ...same as above...,
  "teacher_prefered_teaching_period": [
    {
      "teacher_id": "T1",
      "teacher_name": "Dr. John Smith",
      "day": "tuesday",
      "start_time": "09:00",
      "end_time": "11:00"
    }
  ]
}
```

**Expected:** Classes scheduled on Tuesday between 9-11am (if possible)

**What this tests:**
- ✅ Preference mode works
- ✅ Solver tries to honor preferred times

---

## ✅ Test 4: Teacher Busy Period

**Body:** Same as Test 2, but add:

```json
{
  ...same as above...,
  "teacher_busy_period": [
    {
      "teacher_id": "T1",
      "teacher_name": "Dr. John Smith",
      "day": "monday",
      "start_time": "14:00",
      "end_time": "17:00"
    }
  ]
}
```

**Expected:** NO classes for Dr. Smith on Monday 2pm-5pm

**What this tests:**
- ✅ Hard constraint: teacher busy periods are respected
- ✅ No scheduling conflicts

---

## ✅ Test 5: Course Type Matching

**Body:**
```json
{
  "teachers": [
    {"teacher_id": "T1", "name": "Dr. Lab Expert"}
  ],
  "teacher_courses": [
    {
      "course_id": "BIO301",
      "course_title": "Biology Lab",
      "course_credit": 3,
      "course_type": "practical",  ⬅️ PRACTICAL
      "course_hours": 90,
      "teacher_id": "T1",
      "teacher_name": "Dr. Lab Expert"
    }
  ],
  "halls": [
    {
      "hall_id": "LAB2",
      "hall_name": "Biology Lab",
      "hall_capacity": 25,
      "hall_type": "lab"  ⬅️ LAB
    },
    {
      "hall_id": "R101",
      "hall_name": "Lecture Room",
      "hall_capacity": 50,
      "hall_type": "lecture"  ⬅️ LECTURE
    }
  ],
  ...rest same as Test 2...
}
```

**Expected:** Biology Lab scheduled in "Biology Lab" (lab hall), NOT in "Lecture Room"

**What this tests:**
- ✅ Course type matches hall type
- ✅ Practical → Lab, Theory → Lecture

---

## ❌ Test 6: Infeasible Schedule

**Body:**
```json
{
  "teachers": [
    {"teacher_id": "T1", "name": "Dr. Overworked"}
  ],
  "teacher_courses": [
    {
      "course_id": "HUGE",
      "course_title": "Impossible Course",
      "course_credit": 10,
      "course_type": "theory",
      "course_hours": 3000,  ⬅️ 3000 minutes!
      "teacher_id": "T1",
      "teacher_name": "Dr. Overworked"
    }
  ],
  "halls": [
    {"hall_id": "R1", "hall_name": "Room 1", "hall_capacity": 50, "hall_type": "lecture"}
  ],
  "teacher_busy_period": [],
  "teacher_prefered_teaching_period": [],
  "hall_busy_periods": [],
  "break_period": {
    "start_time": "12:00",
    "end_time": "13:00",
    "daily": true
  },
  "operational_period": {
    "start_time": "08:00",
    "end_time": "10:00",  ⬅️ Only 2 hours per day!
    "daily": true,
    "days": ["monday"],  ⬅️ Only 1 day!
    "constrains": []
  },
  "soft_constrains": {}
}
```

**Expected Response:**
```json
{
  "timetable": [],
  "status": "INFEASIBLE",
  "messages": {
    "error_message": [
      {
        "title": "Insufficient time",
        "message": "Cannot schedule 3000 minutes in 120 minutes of available time"
      }
    ]
  }
}
```

**What this tests:**
- ✅ Graceful failure when impossible
- ✅ Clear error messages

---

## 🐛 Common Issues & Solutions

### Issue: "Connection refused"
**Cause:** Server not running  
**Fix:** Run `make run` in terminal

---

### Issue: 422 Validation Error
**Example error:**
```json
{
  "detail": [
    {
      "loc": ["body", "teacher_busy_period", 0, "day"],
      "msg": "Field required"
    }
  ]
}
```

**Causes:**
1. Using `day_of_week` instead of `day`
2. Missing required field
3. Wrong data type (string vs number)

**Fix:** Check your JSON against the schema carefully

---

### Issue: Status = "INFEASIBLE"
**Cause:** Constraints conflict (impossible to satisfy all rules)

**Common reasons:**
- Not enough time slots for all courses
- Teacher busy during all available times
- No matching hall type (practical course but only lecture halls)
- Break period covers all operational hours

**Fix:**
- Increase operational hours
- Add more days
- Remove some busy periods
- Add appropriate hall types

---

### Issue: Empty timetable but status = "OPTIMAL"
**Cause:** All courses scheduled but not in the returned days (edge case bug)

**Fix:** Check that operational days are spelled correctly (lowercase)

---

## 📊 Response Status Meanings

| Status | Meaning |
|--------|---------|
| `OPTIMAL` | Found the best possible schedule ✅ |
| `FEASIBLE` | Found a valid schedule (maybe not optimal) ✅ |
| `INFEASIBLE` | Impossible to schedule with given constraints ❌ |
| `ERROR` | Solver error (report bug) ❌ |

---

## 🎯 Tips for Testing

1. **Start simple** - 1 teacher, 1 course, 1 hall
2. **Add complexity gradually** - Add busy periods, then preferences, then more teachers
3. **Check solve time** - Should be under 5 seconds for medium datasets
4. **Verify constraints** - Check that busy periods are respected, course types match halls
5. **Test edge cases** - Empty inputs, impossible schedules, minimal time

---

## 📋 Quick Checklist

Before submitting a request, verify:

- [ ] All `teacher_id` match between teachers and teacher_courses
- [ ] `course_type` is either "theory" or "practical"
- [ ] `hall_type` is either "lecture" or "lab"
- [ ] Times are in HH:MM format (e.g., "08:00", not "8:00am")
- [ ] Days are lowercase ("monday", not "Monday")
- [ ] `course_hours` is in minutes
- [ ] Field name is `day`, not `day_of_week`
- [ ] All required fields present (check error message if 422)

---

## 🚀 Next Steps

1. Test all 6 scenarios above
2. Modify the requests to fit your actual school data
3. Check response times (should be fast)
4. Verify timetable looks reasonable
5. Report any issues or unexpected behavior

Happy testing! 🎉
