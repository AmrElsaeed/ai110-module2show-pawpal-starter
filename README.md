# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Paste a sample of your app's CLI or Streamlit output here so a reader can see what a generated plan looks like:

```
==================================================
Today's Schedule - Sunday, October 18, 2026
Owner: Sam | Pets: Rex, Mochi
==================================================
Plan for Sam on 2026-10-18 (85 min scheduled)
  07:00-07:10  Rex: medication - Joint supplement  [pinned at preferred time]
  07:30-08:00  Rex: walk - Morning walk  [high priority, at/after preferred time]
  08:05-08:20  Mochi: play - Feather wand  [low priority, first open slot]
  17:30-17:50  Rex: training - Sit and stay practice  [medium priority, at/after preferred time]
  18:00-18:10  Mochi: feeding - Wet food  [high priority, at/after preferred time]
--------------------------------------------------
Valid plan: True
```

## 🧪 Testing PawPal+

```bash
# Run the full test suite:
pytest

# Run with coverage:
pytest --cov
```

Sample test output:

```
==================================================================================== test session starts =====================================================================================
platform win32 -- Python 3.10.11, pytest-9.1.1, pluggy-1.7.0
rootdir: C:\Drive D\Courses\codepath\AI101\module3\ai110-module2show-pawpal-starter
plugins: anyio-4.15.1
collected 23 items                                                                                                                                                                            

tests\test_pawpal.py .......................                                                                                                                                            [100%]

===================================================================================== 23 passed in 0.15s =====================================================================================
```

## 📐 Smarter Scheduling

All of this lives in `pawpal_system.py`, is shown in `main.py`, and is wired into the Streamlit UI in `app.py`.

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Sorting by time | `sort_by_time()`, `insert_by_time()` | Module-level functions. Order by scheduled start, unscheduled tasks last, ties by priority then id. |
| Sorting by priority | `Scheduler.sort_by_priority()` | Highest priority first, then shortest, then id. Used when placing tasks. |
| Filtering | `Owner.filter_tasks()`, `filter_tasks()`, `Task.status()` | By pet name and/or completion status (also task type and `done`/`overdue`/`pending`). |
| Conflict detection | `detect_conflicts()`, `Scheduler.conflict_warnings()`, `Scheduler.conflicts()` | Overlap check in one sorted pass. Returns warning text, never raises. |
| Recurring tasks | `Task.mark_complete()`, `Task.next_occurrence()`, `Pet.complete_task()`, `Scheduler.complete_task()` | Completing a daily/weekly task spawns the next instance. |
| Extra helpers | `Scheduler.suggest_slot()`, `overload_minutes()`, `pinned_warnings()`, `next_task()`, `grouped_by_pet()` | Free-slot suggestions, overload and skipped-pin warnings, "next up", per-pet grouping. |

### Sorting

- `sort_by_time(tasks)` returns tasks ordered by `scheduled_start`. Tasks with no start time go last, and ties go to the higher priority. `Scheduler.generate()` uses it so the plan is always in time order.
- `insert_by_time(plan, task)` adds one task to an already-sorted plan with a binary search (`bisect`) instead of re-sorting.
- `Scheduler.sort_by_priority()` decides the order tasks are *placed* in: highest priority first, shortest first on ties. Placement is greedy first-fit.

### Filtering

- `Owner.filter_tasks(pet_name=None, completed=None)` narrows all of an owner's tasks. A filter left as `None` is ignored, pet names are case-insensitive, and an unknown pet returns `[]`.
- The module-level `filter_tasks(tasks, owner, pet_name, status, completed, task_type)` does the work and also filters by task type and by status.
- `Task.status()` returns `done`, `overdue` (due date passed, not done) or `pending`.

### Conflict detection

- `detect_conflicts(tasks, buffer)` sorts scheduled tasks by start time and sweeps once (O(n log n)), comparing each task to the latest-ending one before it. It counts the owner's buffer minutes, covers the same pet and different pets, and ignores unscheduled tasks.
- `Scheduler.conflict_warnings()` turns those into readable messages such as `Conflict between Rex and Mochi: Rex training (17:30-17:50) overlaps Mochi play (17:30-17:50)`. It never raises. If something goes wrong it returns a "Could not check" message. It can check the current plan or any list of tasks you pass in.
- The generated plan never overlaps on its own, so warnings appear when tasks are hand-placed or moved (the UI has a "Move a task" form). `explain_plan()` includes them too.
- Tradeoff: with several overlaps it reports each task against the latest-ending earlier task, so it may list fewer pairs than exist. See `reflection.md`.

### Recurring tasks

- `Task.mark_complete(on)` marks the task done (kept as history) and returns the next occurrence for a recurring task, or `None` for a one-off.
- `Task.next_occurrence(on)` builds that new pending copy via `Task.next_due_after()`: +1 day for daily, +7 days for weekly, calendar month for monthly (clamped to month end, so Jan 31 becomes Feb 28), or the next chosen weekday when `weekdays` is set.
- `Pet.complete_task(task_id, on)` and `Scheduler.complete_task(task_id, on)` call `mark_complete` and attach the new task to the right pet. Missed days are not replayed: one next occurrence is created however overdue the task was.
- `Task.is_due_on(day)` skips completed tasks and respects the due date, weekdays and last completion.

## Shory Implementation Summary

PawPal is a small pet-care scheduler. All the logic is in pawpal_system.py, with a demo in main.py and two tests in tests/test_pawpal.py.

There are four classes:

Task is one thing a pet needs done, like a walk or a dose of medication. It has a duration, a priority, how often it repeats and, optionally, a time you'd like it done. If you mark that time as fixed, the scheduler treats it as a must. Otherwise it's just a hint. Once the scheduler runs, it stamps each task with a start and end time.
Pet holds the pet's details and its list of tasks.
Owner holds the person's pets and when they're free: open windows, blocked-off times, a gap to leave between tasks and, if you want one, a cap on total minutes per day.
Scheduler takes an owner and works out a plan for one day.
The pieces connect in a chain. The owner has pets, the pets have tasks, and the scheduler walks that chain to collect everything due that day. It puts the fixed-time tasks in first, then fills the gaps with everything else, most important first, using the earliest slot that fits. If something doesn't fit, it's set aside with a note saying why. 

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
