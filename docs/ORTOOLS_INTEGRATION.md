OR-Tools Integration & Scheduling API — Summary
===============================================

Date: 2025-11-02
Repository: sss-schedule-api

Purpose
-------
This short document summarizes the current scheduling system, issues to fix, and a concrete plan to integrate Google OR-Tools to build reliable scheduling APIs. Use this as a shareable brief for teammates or stakeholders.

What the current system contains
--------------------------------
- FastAPI application entry: `main.py`.
- Pydantic models: `models/schemas.py` describing teachers, halls, availability/busy times, constraints, `SchedulingRequest`, and `SchedulingResponse`.
- Router: `routers/schedule.py` exposing a POST `/api/schedule` endpoint.
- A naive scheduler at `service/scheduler.py` that currently uses randomized assignment and constraint checks.

Key issues observed (must fix before OR-Tools work)
---------------------------------------------------
1. Import mismatch: router imports `ORToolsScheduler` but only `Scheduler` exists in `service/scheduler.py`.
2. Pydantic access errors: code treats request and constraints like dictionaries (e.g. `self.request.constraints['school_start_time']`) instead of attribute access or `.dict()`.
3. Time handling inconsistencies: mixing ISO datetimes and HH:MM strings with naive datetime comparisons — fragile and may break across timezones.
4. No persistence or job handling: solver runs synchronously making large problems impractical.
5. No dependency manifest found (add `requirements.txt` or `pyproject.toml`) and `ortools` is missing.
6. No tests or CI and limited logging.

Why OR-Tools and recommended solver
----------------------------------
Use Google OR-Tools CP-SAT (`ortools.sat.python.cp_model`) because:
- It efficiently solves boolean assignment problems and supports optimization objectives.
- It scales better and can provide guaranteed optimality or best-effort solutions within time limits.
- It supports linear/quasi-linear soft constraints via weighted objectives.

Mapping the scheduling problem to CP-SAT
---------------------------------------
1. Discretize time into slots using `constraints.lesson_slot_length` between `school_start_time` and `school_end_time` for each weekday.
2. Indices:
   - days: Monday..Friday (or configurable)
   - slots per day: S
   - halls: H
   - courses or course-instances: C
3. Decision variables: x[c, d, s, h] ∈ {0,1} → course c scheduled on day d at slot s in hall h.
4. Hard constraints to encode:
   - Course frequency per week matches requested frequency.
   - Teacher availability: teacher cannot be assigned outside available times or during busy times.
   - Hall availability: halls cannot host more than one course per slot and respect busy times.
   - No teacher or hall conflicts: one course per teacher/hall per slot.
   - Min/max courses per teacher per day, max consecutive classes, lunch break exclusion.
   - Weekly load limits (sum of assigned slots × slot length).
5. Soft objectives (optional): minimize teacher gaps, balance load across days, minimize number of teachers above recommended load. Model via weighted linear objective.

Scalability notes
-----------------
- Variable count = C × D × S × H. For large inputs this can grow quickly.
- Reduce model size by filtering infeasible (teacher/hall unavailable) slot/hall pairs before creating variables.
- Consider modeling course frequencies (counts) rather than unique instances where appropriate.
- Always run with a time limit and return best-found solution if optimality is not reached.

API design — two scheduling APIs
-------------------------------
1) Synchronous solver (fast, for small problems)
   - POST /api/schedule/solve
   - Accepts: `SchedulingRequest`
   - Returns: `SchedulingResponse` containing schedule, `is_optimal`, and `solution_info`.
   - Behavior: run CP-SAT with a short timeout (e.g. 5–30s) and return best solution.

2) Asynchronous job-based solver (for large/production runs)
   - POST /api/schedule/jobs  → enqueues a scheduling job and returns {job_id, status}
   - GET /api/schedule/jobs/{job_id} → returns job status and, if finished, the `SchedulingResponse` or download link.
   - Implementation: use Celery + Redis (or RQ) and persist job results (Postgres or file storage). Useful for longer runs and retries.

Minimal file-level changes to implement (priority order)
-------------------------------------------------------
- `service/ortools_solver.py` (new): Implement `ORToolsScheduler` class with `solve_scheduling(request: SchedulingRequest) -> SchedulingResponse`.
- `service/scheduler.py` (update): Either keep the existing `Scheduler` as a fallback/testing helper or refactor to use common utilities (time parsing, slot generation) used by OR-Tools module.
- `routers/schedule.py` (update): Fix import to use `ORToolsScheduler` and add endpoints for synchronous `/solve` and asynchronous `/jobs` (if implementing async now).
- `requirements.txt` (new): Add `fastapi`, `uvicorn`, `pydantic`, `ortools` pinned versions.
- `tests/` (new): Add unit tests for solver (small synthetic cases) and an integration test for the API route.
- Optional: `docker-compose.yml` with Redis for async worker + Celery.

Implementation checklist (short-term MVP)
-----------------------------------------
1. Fix router import bug and Pydantic attribute access in existing code.
2. Add `requirements.txt` and install `ortools` in dev environment.
3. Add `service/ortools_solver.py` that:
   - canonicalizes times to slot indices
   - builds CP-SAT model with filtered variables
   - solves with configurable time limit
   - returns `SchedulingResponse` (best solution + status)
4. Wire `/api/schedule/solve` to call the OR-Tools solver synchronously.
5. Add a small test that submits a minimal `SchedulingRequest` (1 teacher, 1 course, 1 hall) and expects a valid schedule.
6. Add logs and clear `solution_info` strings describing solver status (OPTIMAL, FEASIBLE, INFEASIBLE, TIME_LIMIT).

Medium-term (production hardening)
----------------------------------
- Implement asynchronous job queue and persistence (Celery+Redis + Postgres).
- Add validation and richer constraint translations (consecutive slots, soft constraints weights).
- Add monitoring (request latency, solver time), metrics, structured logging and request tracing.
- Containerize app and worker; add CI for tests; pin and audit dependencies.

Suggested first implementation task (recommended)
------------------------------------------------
Implement the minimal OR-Tools integration and expose `/api/schedule/solve`. This gives a runnable proof-of-concept and quick feedback on model quality and scaling.

Quick shareable summary (one paragraph)
--------------------------------------
We will replace the current randomized generator with a CP-SAT model using OR-Tools. Time will be discretized into lesson slots and the model will use boolean variables x[course,day,slot,hall] to enforce availability, hall and teacher conflicts, frequency and load constraints, with optional soft objectives. Start by adding `service/ortools_solver.py`, fixing a few pydantic/time handling bugs, and wiring a synchronous `/api/schedule/solve` endpoint; later add an asynchronous job API with Celery/Redis for large runs.

Next steps for me (if you want me to continue)
----------------------------------------------
- I can implement the MVP OR-Tools solver and wire it to a new `/api/schedule/solve` endpoint (recommended).
- Or I can build an async job runner with Celery and persistence.

Contact / author
----------------

