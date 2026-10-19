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
# Paste your pytest output here
```

## 📐 Smarter Scheduling

> Fill in once you've implemented scheduling logic.

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | | e.g., by priority, duration |
| Filtering | | e.g., skip tasks if time runs out |
| Conflict handling | | e.g., overlapping time slots |
| Recurring tasks | | e.g., daily vs. weekly |

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
