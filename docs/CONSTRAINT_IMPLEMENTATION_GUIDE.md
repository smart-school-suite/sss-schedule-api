# OR-Tools Constraint Implementation Guide

## Overview

This document maps the 30+ soft constraints from the API specification to their OR-Tools CP-SAT implementation strategy.

## Constraint Categories

### 1. Teacher Constraints

#### 1.1 Maximum Daily Teaching Hours
**API Field**: `soft_constrains.teacher_max_daily_hours`  
**Type**: Decimal (hours)  
**Implementation**:
```python
# For each teacher t, each day d:
# Sum of (slot duration × assigned slots) ≤ max_daily_hours
daily_hours = []
for day in days:
    hours_var = model.NewIntVar(0, 1440, f'teacher_{t}_day_{day}_hours')
    model.Add(hours_var == sum(x[c,d,s,h] * slot_duration 
                                for all c,s,h where teacher(c)==t))
    daily_hours.append(hours_var)
    model.Add(hours_var <= max_daily_hours * 60)

# Add to objective with weight
objective_terms.append(-sum(deviation from ideal))
```

#### 1.2 Maximum Weekly Teaching Hours
**API Field**: `soft_constrains.teacher_max_weekly_hours`  
**Type**: Decimal (hours)  
**Implementation**:
```python
# For each teacher t:
weekly_hours = sum(x[c,d,s,h] * slot_duration 
                   for all c,d,s,h where teacher(c)==t)
model.Add(weekly_hours <= max_weekly_hours * 60)
```

#### 1.3 Minimum Break Between Classes
**API Field**: `soft_constrains.teacher_minimum_break_between_classes`  
**Type**: Integer (number of free periods)  
**Implementation**:
```python
# For each teacher t, day d, consecutive slot pairs (s, s+1):
# If teacher has class at slot s:
#   Then teacher cannot have class at slots s+1, s+2, ..., s+min_break
for s in range(len(slots) - min_break):
    for c1 in courses_for_teacher[t]:
        # If scheduled at s, block next min_break slots
        model.Add(sum(x[c2,d,s+i,h] 
                     for c2 in courses_for_teacher[t]
                     for i in range(1, min_break+1)
                     for h in halls) == 0).OnlyEnforceIf(x[c1,d,s,h])
```

#### 1.4 Even Subject Distribution
**API Field**: `soft_constrains.teacher_even_subject_distribution`  
**Type**: Boolean  
**Implementation**:
```python
# Minimize variance of courses per day across the week
# For teacher t:
courses_per_day = [count of courses on day d for d in days]
mean_courses = sum(courses_per_day) / len(days)
variance = sum((count - mean_courses)^2 for count in courses_per_day)

# Minimize variance in objective
objective_terms.append(-variance * weight)
```

#### 1.5 Balanced Workload
**API Field**: `soft_constrains.teacher_balanced_workload`  
**Type**: Boolean  
**Implementation**:
```python
# Balance load across all teachers in the same department
# Calculate deviation from mean workload
teacher_loads = {t: total_hours(t) for t in teachers}
mean_load = sum(teacher_loads.values()) / len(teachers)
deviation = sum(abs(load - mean_load) for load in teacher_loads.values())

objective_terms.append(-deviation * weight)
```

#### 1.6 Avoid Split Double Periods
**API Field**: `soft_constrains.teacher_avoid_split_double_periods`  
**Type**: Boolean  
**Implementation**:
```python
# For multi-credit courses requiring multiple consecutive periods:
# Encourage consecutive slot assignment
for course in courses where credit > 1:
    for d, s in all_day_slot_pairs:
        # Bonus if consecutive slots assigned
        consecutive_var = model.NewBoolVar(f'consecutive_{course}_{d}_{s}')
        model.Add(x[course,d,s,h] + x[course,d,s+1,h] == 2).OnlyEnforceIf(consecutive_var)
        objective_terms.append(consecutive_var * weight)
```

---

### 2. Course Constraints

#### 2.1 Course Load Proportionality
**API Field**: `soft_constrains.course_load_proportionality`  
**Type**: Boolean  
**Implementation**:
```python
# Higher-credit courses should appear more frequently
# Ensure sessions_per_week proportional to credit hours
for course in courses:
    expected_sessions = course.credit * proportionality_factor
    actual_sessions = sum(x[course,d,s,h] for all d,s,h)
    deviation = abs(actual_sessions - expected_sessions)
    objective_terms.append(-deviation * weight)
```

#### 2.2 Avoid Clustering of Same Course
**API Field**: `soft_constrains.course_avoid_clustering`  
**Type**: Boolean  
**Implementation**:
```python
# Prevent same course from being scheduled on consecutive days
for course in courses:
    for d1, d2 in consecutive_day_pairs:
        has_d1 = sum(x[course,d1,s,h] for all s,h) >= 1
        has_d2 = sum(x[course,d2,s,h] for all s,h) >= 1
        penalty_var = model.NewBoolVar(f'clustered_{course}_{d1}_{d2}')
        model.Add(has_d1 + has_d2 == 2).OnlyEnforceIf(penalty_var)
        objective_terms.append(-penalty_var * weight)
```

#### 2.3 Minimum Gap Between Course Sessions
**API Field**: `soft_constrains.course_minimum_gap_between_sessions`  
**Type**: Integer (hours/days)  
**Implementation**:
```python
# Ensure at least N days between same course sessions
for course in courses:
    session_days = [d for d in days if sum(x[course,d,s,h]) > 0]
    for i in range(len(session_days) - 1):
        gap = day_index(session_days[i+1]) - day_index(session_days[i])
        model.Add(gap >= min_gap_days)
```

#### 2.4 Course Room Suitability
**API Field**: `soft_constrains.course_room_suitability`  
**Type**: Object `{"theory": "lecture", "practical": "lab"}`  
**Implementation**:
```python
# HARD CONSTRAINT: Only create variables for suitable halls
for course in courses:
    suitable_halls = filter_halls_by_type(course.type, suitability_mapping)
    # Only create x[course,d,s,h] for h in suitable_halls
```

#### 2.5 Course Preferred Time of Day
**API Field**: `soft_constrains.course_preferred_time_of_day`  
**Type**: Object `{"theory": "morning", "practical": "evening"}`  
**Implementation**:
```python
# SOFT CONSTRAINT: Bonus for scheduling in preferred time
morning_slots = [s for s in slots if slot_time(s) < "12:00"]
evening_slots = [s for s in slots if slot_time(s) >= "14:00"]

for course in courses:
    preferred_slots = morning_slots if course.type == "theory" else evening_slots
    preference_bonus = sum(x[course,d,s,h] 
                          for d,s,h where s in preferred_slots)
    objective_terms.append(preference_bonus * weight)
```

#### 2.6 Credit-Hour Density Control
**API Field**: `soft_constrains.course_credit_hour_density_control`  
**Type**: Boolean  
**Implementation**:
```python
# Prevent too many high-credit courses in a single day
for day in days:
    daily_credit_load = sum(x[c,d,s,h] * course[c].credit 
                           for all c,s,h)
    model.Add(daily_credit_load <= max_daily_credit_threshold)
```

#### 2.7 Course Spread Across Week
**API Field**: `soft_constrains.course_spread_across_week`  
**Type**: Boolean  
**Implementation**:
```python
# Encourage courses to be distributed across different days
for course in courses where sessions_needed > 1:
    unique_days_var = model.NewIntVar(0, len(days), f'unique_days_{course}')
    # Count distinct days where course appears
    # Maximize unique_days_var
    objective_terms.append(unique_days_var * weight)
```

---

### 3. Hall Constraints

#### 3.1 Hall Capacity Limit
**API Field**: `soft_constrains.hall_capacity_limit`  
**Type**: Boolean  
**Implementation**:
```python
# Ensure course enrollment ≤ hall capacity
# Note: Requires student group size data (not in current API)
for course, hall in all_course_hall_pairs:
    if enrollment[course] > hall.capacity:
        # Don't create variable x[course,d,s,hall] or set to 0
        pass
```

#### 3.2 Hall Type Suitability
**API Field**: `soft_constrains.hall_type_suitability`  
**Type**: Object `{"theory": "lecture", "practical": "lab"}`  
**Implementation**:
```python
# Same as course_room_suitability - filter hall variables by type
```

#### 3.3 Hall Change Minimization
**API Field**: `soft_constrains.hall_change_minimization`  
**Type**: Boolean  
**Implementation**:
```python
# Minimize number of different halls used by same teacher in one day
for teacher in teachers:
    for day in days:
        halls_used = set of halls where teacher has classes
        penalty = len(halls_used) - 1  # Penalty for each additional hall
        objective_terms.append(-penalty * weight)
```

#### 3.4 Hall Usage Balance
**API Field**: `soft_constrains.hall_usage_balance`  
**Type**: Boolean  
**Implementation**:
```python
# Balance usage across all halls
hall_usage = {h: sum(x[c,d,s,h] for all c,d,s) for h in halls}
mean_usage = sum(hall_usage.values()) / len(halls)
variance = sum((usage - mean_usage)^2 for usage in hall_usage.values())
objective_terms.append(-variance * weight)
```

---

### 4. Time Constraints

#### 4.1 Max Periods Per Day
**API Field**: `soft_constrains.time_max_periods_per_day`  
**Type**: Integer  
**Implementation**:
```python
# For each teacher/class and day:
periods_count = sum(x[c,d,s,h] for all c,s,h)
model.Add(periods_count <= max_periods_per_day)
```

#### 4.2 Min Free Periods Per Day
**API Field**: `soft_constrains.time_min_free_periods_per_day`  
**Type**: Integer  
**Implementation**:
```python
# For each teacher and day:
total_slots = len(slots_per_day[d])
used_slots = sum(x[c,d,s,h] for all c,s,h)
free_slots = total_slots - used_slots
model.Add(free_slots >= min_free_periods)
```

#### 4.3 Balanced Daily Workload
**API Field**: `soft_constrains.time_balanced_daily_workload`  
**Type**: Boolean  
**Implementation**:
```python
# Minimize variance of periods per day for each teacher
for teacher in teachers:
    periods_per_day = [count for each day]
    mean_periods = sum(periods_per_day) / len(days)
    variance = sum((count - mean_periods)^2 for count in periods_per_day)
    objective_terms.append(-variance * weight)
```

#### 4.4 Balanced Weekly Workload
**API Field**: `soft_constrains.time_balanced_weekly_workload`  
**Type**: Boolean  
**Implementation**:
```python
# Balance weekly load across all teachers
teacher_weekly_loads = {t: total_periods(t) for t in teachers}
mean_load = sum(teacher_weekly_loads.values()) / len(teachers)
deviation = sum(abs(load - mean_load) for load in teacher_weekly_loads.values())
objective_terms.append(-deviation * weight)
```

#### 4.5 Avoid Consecutive Heavy Subjects
**API Field**: `soft_constrains.time_avoid_consecutive_heavy_subjects`  
**Type**: Boolean  
**Implementation**:
```python
# Prevent high-credit courses from being scheduled back-to-back
heavy_threshold = mean(course.credit for course in courses) + std_dev
heavy_courses = [c for c in courses if c.credit >= heavy_threshold]

for d,s in all_day_slot_pairs:
    consecutive_heavy = model.NewBoolVar(f'consecutive_heavy_{d}_{s}')
    model.Add(sum(x[c,d,s,h] + x[c,d,s+1,h] 
                 for c in heavy_courses 
                 for h in halls) == 2).OnlyEnforceIf(consecutive_heavy)
    objective_terms.append(-consecutive_heavy * penalty_weight)
```

#### 4.6 Consecutive Period Allowance
**API Field**: `soft_constrains.time_consecutive_period_allowance`  
**Type**: Object `{"practicals": bool, "theory": bool}`  
**Implementation**:
```python
# Allow/encourage consecutive periods for specified course types
for course_type, allowed in consecutive_allowance.items():
    if allowed:
        # Bonus for consecutive scheduling
        for course in courses where type == course_type:
            for d,s in day_slot_pairs:
                consecutive_var = model.NewBoolVar(f'consec_{course}_{d}_{s}')
                model.Add(x[course,d,s,h] + x[course,d,s+1,h] == 2).OnlyEnforceIf(consecutive_var)
                objective_terms.append(consecutive_var * bonus_weight)
```

#### 4.7 Min Gap Between Sessions
**API Field**: `soft_constrains.time_min_gap_between_sessions`  
**Type**: Decimal (minutes)  
**Implementation**:
```python
# Enforce minimum transition time between any two sessions
# This is typically handled by slot discretization
# Ensure slot_duration >= min_gap or add buffer slots
```

#### 4.8 Subject Frequency Per Day
**API Field**: `soft_constrains.time_subject_frequency_per_day`  
**Type**: Integer  
**Implementation**:
```python
# Limit how many times same course appears in one day
for course in courses:
    for day in days:
        occurrences = sum(x[course,d,s,h] for all s,h)
        model.Add(occurrences <= max_subject_frequency_per_day)
```

---

## Objective Function Structure

```python
# Weighted sum of all soft constraint terms
objective = sum(weight_i * term_i for all soft constraints)

# Maximize the objective
model.Maximize(objective)
```

### Default Weights (tunable)

```python
WEIGHTS = {
    'teacher_preference': 100,
    'load_balance': 50,
    'avoid_gaps': 30,
    'consecutive_periods': 20,
    'hall_minimization': 15,
    'time_preference': 10,
    # ... etc
}
```

## Implementation Priority

### Phase 1: Critical Hard Constraints
1. No overlapping (teacher/hall)
2. Course frequency requirements
3. Busy period enforcement
4. Break period enforcement
5. Hall type matching

### Phase 2: High-Priority Soft Constraints
1. Teacher preferences
2. Load balancing
3. Avoid gaps
4. Consecutive period handling

### Phase 3: Refinement Constraints
1. Hall usage balance
2. Credit density control
3. Time-of-day preferences
4. Advanced distribution constraints

## Testing Strategy

1. **Unit test each constraint** with minimal cases
2. **Integration test** with full request
3. **Benchmark** solve times for various problem sizes
4. **Validate determinism** (same input → same output)
5. **Test infeasibility detection** (conflicting constraints)

## Performance Optimization

1. **Pre-filter variables**: Only create x[c,d,s,h] for feasible combinations
2. **Use hints**: Provide warm-start solutions from heuristics
3. **Symmetry breaking**: Add constraints to eliminate equivalent solutions
4. **Parallel search**: Use multiple workers for large problems
5. **Time limits**: Set reasonable timeouts with partial solution extraction
