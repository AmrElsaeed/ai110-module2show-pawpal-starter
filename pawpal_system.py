"""PawPal logic layer: four backend classes (Owner, Pet, Task, Scheduler)."""

from __future__ import annotations

import bisect
import calendar
import csv
import io
import json
from dataclasses import dataclass, field, replace
from datetime import date, datetime, time, timedelta
from itertools import count
from typing import Any, Literal, Optional

TaskType = Literal["feeding", "walk", "medication", "grooming", "play", "vet_visit", "training"]
Priority = Literal["low", "medium", "high", "critical"]
Frequency = Literal["once", "daily", "weekly", "monthly"]

# A window of time within one day, as (start, end). Does not cross midnight.
Window = tuple[time, time]

_PRIORITY_RANK: dict[str, int] = {"low": 1, "medium": 2, "high": 3, "critical": 4}
_FREQUENCY_DAYS: dict[str, int] = {"daily": 1, "weekly": 7, "monthly": 30}

_task_ids = count(1)
_pet_ids = count(1)
_owner_ids = count(1)


def _minutes(t: time) -> int:
    """Convert a time of day to minutes since midnight."""
    return t.hour * 60 + t.minute


def _to_time(minutes: int) -> time:
    """Convert minutes since midnight back to a time of day."""
    return time(minutes // 60, minutes % 60)


def _add_months(d: date, months: int = 1) -> date:
    """Add calendar months, clamping to month end (Jan 31 + 1 month = Feb 28/29)."""
    year, month = divmod(d.year * 12 + d.month - 1 + months, 12)
    month += 1
    return d.replace(year=year, month=month,
                     day=min(d.day, calendar.monthrange(year, month)[1]))


def _fmt(t: Optional[time]) -> str:
    """Format a time as HH:MM, or '--:--' if it is None."""
    return t.strftime("%H:%M") if t else "--:--"


@dataclass
class Task:
    """A care task for one pet. `pet_id` is set by Pet.add_task, not by the caller.

    `scheduled_start` / `scheduled_end` are filled in by Scheduler.generate.
    """
    task_type: TaskType
    description: str = ""
    duration_minutes: int = 15
    priority: Priority = "medium"
    frequency: Frequency = "once"
    due_date: Optional[date] = None
    last_completed: Optional[date] = None
    # fixed_time=True: preferred_time is a hard pin, placed before everything else.
    # fixed_time=False: preferred_time is a soft hint the scheduler may move.
    preferred_time: Optional[time] = None
    fixed_time: bool = False
    task_id: int = field(default_factory=lambda: next(_task_ids))
    pet_id: Optional[int] = None
    completed: bool = False
    scheduled_start: Optional[time] = None
    scheduled_end: Optional[time] = None
    # Optional weekday set (Mon=0..Sun=6) for a recurring task, e.g. {0, 2, 4}.
    weekdays: Optional[set[int]] = None

    def __post_init__(self) -> None:
        """Validate priority, frequency and duration."""
        if self.priority not in _PRIORITY_RANK:
            raise ValueError(f"Unknown priority: {self.priority!r}")
        if self.frequency != "once" and self.frequency not in _FREQUENCY_DAYS:
            raise ValueError(f"Unknown frequency: {self.frequency!r}")
        if self.duration_minutes <= 0:
            raise ValueError("duration_minutes must be positive")
        if self.weekdays is not None and not all(0 <= d <= 6 for d in self.weekdays):
            raise ValueError("weekdays must be in 0..6 (Mon=0)")

    @property
    def is_recurring(self) -> bool:
        """True if the task repeats (anything other than 'once')."""
        return self.frequency != "once"

    @property
    def priority_rank(self) -> int:
        """Numeric priority (1 = low ... 4 = critical) for sorting."""
        return _PRIORITY_RANK[self.priority]

    def next_due_after(self, on: date) -> date:
        """The next due date after completing on `on`, per frequency/weekdays."""
        if self.weekdays:
            day = on + timedelta(days=1)
            while day.weekday() not in self.weekdays:
                day += timedelta(days=1)
            return day
        if self.frequency == "monthly":
            return _add_months(on, 1)
        return on + timedelta(days=_FREQUENCY_DAYS[self.frequency])

    def is_due_on(self, day: date) -> bool:
        """True if this task belongs on `day`, based on frequency, due_date and last_completed."""
        if self.completed:
            return False
        if not self.is_recurring:
            return self.due_date is None or self.due_date <= day
        if self.due_date is not None and day < self.due_date:
            return False
        if self.weekdays:
            return day.weekday() in self.weekdays
        if self.last_completed is not None:
            if self.frequency == "monthly":
                return day >= _add_months(self.last_completed, 1)
            if (day - self.last_completed).days < _FREQUENCY_DAYS[self.frequency]:
                return False
        return True

    def status(self, today: Optional[date] = None) -> str:
        """'done', 'overdue' (past due_date, not done) or 'pending'."""
        if self.completed:
            return "done"
        today = today or date.today()
        if self.due_date is not None and self.due_date < today:
            return "overdue"
        return "pending"

    def mark_complete(self, on: Optional[date] = None) -> Optional["Task"]:
        """Mark this task done and return the next occurrence if it recurs.

        The finished task is kept as history. For a recurring task (daily,
        weekly, monthly or weekdays) a fresh, pending copy due on the next
        date is returned; one-off tasks return None. The caller attaches the
        copy to a pet - use Pet.complete_task or Scheduler.complete_task to
        have that done automatically.
        """
        on = on or date.today()
        nxt = self.next_occurrence(on)
        self.last_completed = on
        self.completed = True
        return nxt

    def next_occurrence(self, on: Optional[date] = None) -> Optional["Task"]:
        """Fresh copy of a recurring task due at its next date, or None for one-offs."""
        if not self.is_recurring:
            return None
        on = on or date.today()
        return replace(self, task_id=next(_task_ids), completed=False, last_completed=None,
                       due_date=self.next_due_after(on),
                       scheduled_start=None, scheduled_end=None)

    def is_urgent(self) -> bool:
        """True if priority is high or critical."""
        return self.priority in ("high", "critical")


@dataclass
class Pet:
    """Pet info. Owns its tasks."""
    pet_name: str
    species: str = ""
    breed: str = ""
    age: int = 0
    weight_kg: float = 0.0
    medical_notes: str = ""
    pet_id: int = field(default_factory=lambda: next(_pet_ids))
    owner_id: Optional[int] = None           # set by Owner.add_pet
    tasks: list[Task] = field(default_factory=list)

    _EDITABLE = ("pet_name", "species", "breed", "age", "weight_kg", "medical_notes")

    def get_summary(self) -> str:
        """Return a one-line description of the pet."""
        parts = [self.pet_name]
        details = ", ".join(str(x) for x in (self.species, self.breed) if x)
        if details:
            parts.append(f"({details})")
        parts.append(f"age {self.age}")
        if self.weight_kg:
            parts.append(f"{self.weight_kg:g} kg")
        summary = " ".join(parts)
        if self.medical_notes:
            summary += f" - notes: {self.medical_notes}"
        return summary

    def update_info(self, **changes: Any) -> None:
        """Update known fields only; raise AttributeError on unknown names."""
        unknown = [k for k in changes if k not in self._EDITABLE]
        if unknown:
            raise AttributeError(f"Cannot update unknown/protected field(s): {', '.join(unknown)}")
        for key, value in changes.items():
            setattr(self, key, value)

    def add_task(self, task: Task) -> None:
        """Append task and set task.pet_id = self.pet_id."""
        if any(t.task_id == task.task_id for t in self.tasks):
            return
        task.pet_id = self.pet_id
        self.tasks.append(task)

    def remove_task(self, task_id: int) -> None:
        """Remove the task with the given id, if present."""
        self.tasks = [t for t in self.tasks if t.task_id != task_id]

    def tasks_due_on(self, day: date) -> list[Task]:
        """Return this pet's tasks that are due on `day`."""
        return [t for t in self.tasks if t.is_due_on(day)]

    def complete_task(self, task_id: int, on: Optional[date] = None) -> Optional[Task]:
        """Complete a task, keeping it as history; recurring tasks spawn the next one.

        Returns the newly spawned task (or None). Missed days are not replayed:
        only one next occurrence is created, however overdue the task was.
        """
        task = next((t for t in self.tasks if t.task_id == task_id), None)
        if task is None:
            raise KeyError(f"No task with id {task_id}")
        nxt = task.mark_complete(on)
        if nxt is not None:
            self.add_task(nxt)
        return nxt


@dataclass
class Owner:
    """The pet owner, their pets, and their availability.

    Availability rule: `available_time` holds the real windows. `day_start` /
    `day_end` are only a fallback used when `available_time` is empty.
    `blocked_times` are always subtracted from whatever windows result.
    """
    owner_name: str
    email: str = ""
    owner_id: int = field(default_factory=lambda: next(_owner_ids))
    pets: list[Pet] = field(default_factory=list)
    available_time: list[Window] = field(default_factory=list)
    blocked_times: list[Window] = field(default_factory=list)
    day_start: time = time(8, 0)
    day_end: time = time(20, 0)
    max_total_minutes: Optional[int] = None  # None = unlimited
    buffer_minutes: int = 5                  # gap required between consecutive tasks
    preferences: list[str] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Append pet and set pet.owner_id = self.owner_id."""
        if any(p.pet_id == pet.pet_id for p in self.pets):
            return
        pet.owner_id = self.owner_id
        self.pets.append(pet)

    def remove_pet(self, pet_id: int) -> None:
        """Remove the pet with the given id, if present."""
        self.pets = [p for p in self.pets if p.pet_id != pet_id]

    def get_pet(self, pet_id: int) -> Optional[Pet]:
        """Return the pet with the given id, or None."""
        return next((p for p in self.pets if p.pet_id == pet_id), None)

    def get_all_tasks(self) -> list[Task]:
        """Flatten tasks from self.pets (pets are the single source of truth)."""
        return [t for p in self.pets for t in p.tasks]

    def filter_tasks(self, pet_name: Optional[str] = None,
                     completed: Optional[bool] = None) -> list[Task]:
        """This owner's tasks, narrowed by pet name and/or completion status.

        A filter left as None is ignored; an unknown pet name returns [].
        """
        return filter_tasks(self.get_all_tasks(), self, pet_name=pet_name, completed=completed)

    def get_pet_by_name(self, name: str) -> Optional[Pet]:
        """Case-insensitive pet lookup by name."""
        return {p.pet_name.lower(): p for p in self.pets}.get(name.strip().lower())

    def add_time_slot(self, window: Window) -> None:
        """Add an availability window, rejecting one whose start isn't before its end."""
        start, end = window
        if start >= end:
            raise ValueError(f"Window start {start} must be before end {end}")
        if window not in self.available_time:
            self.available_time.append(window)

    def remove_time_slot(self, window: Window) -> None:
        """Remove an availability window, if present."""
        if window in self.available_time:
            self.available_time.remove(window)

    def effective_windows(self) -> list[Window]:
        """Resolve available_time / day_start-day_end fallback, minus blocked_times."""
        base = sorted(self.available_time) or [(self.day_start, self.day_end)]
        result: list[tuple[int, int]] = [(_minutes(s), _minutes(e)) for s, e in base]
        for b_start, b_end in self.blocked_times:
            bs, be = _minutes(b_start), _minutes(b_end)
            cut: list[tuple[int, int]] = []
            for ws, we in result:
                if be <= ws or bs >= we:      # no overlap
                    cut.append((ws, we))
                    continue
                if ws < bs:
                    cut.append((ws, bs))
                if be < we:
                    cut.append((be, we))
            result = cut
        return [(_to_time(s), _to_time(e)) for s, e in sorted(result) if s < e]

    def is_available(self, t: time) -> bool:
        """True if `t` falls inside one of the effective windows."""
        return any(start <= t < end for start, end in self.effective_windows())


def sort_by_time(tasks: list[Task]) -> list[Task]:
    """Order by scheduled start (unscheduled last); ties by priority then id."""
    return sorted(tasks, key=lambda t: (t.scheduled_start or time.max,
                                        -t.priority_rank, t.task_id))


def insert_by_time(plan: list[Task], task: Task) -> None:
    """Insert into an already time-sorted plan, keeping it sorted (binary search)."""
    keys = [t.scheduled_start or time.max for t in plan]
    plan.insert(bisect.bisect_right(keys, task.scheduled_start or time.max), task)


def filter_tasks(tasks: list[Task], owner: Optional[Owner] = None,
                 pet_name: Optional[str] = None, status: Optional[str] = None,
                 completed: Optional[bool] = None, task_type: Optional[str] = None,
                 today: Optional[date] = None) -> list[Task]:
    """Keep tasks matching every filter given; a filter left as None is ignored.

    `pet_name` needs `owner` to resolve names; an unknown pet yields no tasks.
    """
    preds = []
    if pet_name is not None:
        pet = owner.get_pet_by_name(pet_name) if owner else None
        pid = pet.pet_id if pet else None
        preds.append(lambda t: pid is not None and t.pet_id == pid)
    if status is not None:
        preds.append(lambda t: t.status(today) == status)
    if completed is not None:
        preds.append(lambda t: t.completed == completed)
    if task_type is not None:
        preds.append(lambda t: t.task_type == task_type)
    return [t for t in tasks if all(p(t) for p in preds)]


def detect_conflicts(tasks: list[Task], buffer: int = 0) -> list[tuple[Task, Task, str]]:
    """Sort-and-sweep overlap check over scheduled tasks, across all pets.

    Each task is compared with the latest-ending task so far, so one long task
    that overlaps several others reports each clash. Returns (earlier, later, message).
    """
    placed = sorted((t for t in tasks if t.scheduled_start and t.scheduled_end),
                    key=lambda t: _minutes(t.scheduled_start))
    found: list[tuple[Task, Task, str]] = []
    latest: Optional[Task] = None
    for cur in placed:
        if latest is not None and (_minutes(cur.scheduled_start)
                                   < _minutes(latest.scheduled_end) + buffer):
            found.append((latest, cur,
                          f"{latest.task_type} ({_fmt(latest.scheduled_start)}-"
                          f"{_fmt(latest.scheduled_end)}) overlaps {cur.task_type} "
                          f"at {_fmt(cur.scheduled_start)}"))
        if latest is None or _minutes(cur.scheduled_end) > _minutes(latest.scheduled_end):
            latest = cur
    return found


@dataclass
class Scheduler:
    """Builds a one-day plan for an owner's pets.

    Algorithm:
      1. Collect tasks due on `schedule_date` (Owner.get_all_tasks + Task.is_due_on).
      2. Place `fixed_time` tasks at their pinned times; any that clash with
         blocked/unavailable time go to `unscheduled_tasks`.
      3. Sort the rest by priority (tie-break: shortest first), then place each
         in the first window with room, honoring `buffer_minutes` and
         `max_total_minutes`. Placement sets task.scheduled_start/end.
      4. Anything that doesn't fit goes to `unscheduled_tasks`.
    The scheduler never creates overlaps, so `validate` only double-checks.
    """
    owner: Owner
    schedule_date: date = field(default_factory=date.today)
    plan: list[Task] = field(default_factory=list)              # scheduled, in time order
    unscheduled_tasks: list[Task] = field(default_factory=list)
    reasons: dict[int, str] = field(default_factory=dict)       # task_id -> why placed/skipped
    generated_at: Optional[datetime] = None

    @property
    def total_duration(self) -> int:
        """Total minutes of all scheduled tasks."""
        return sum(t.duration_minutes for t in self.plan)

    def generate(self) -> None:
        """Rebuild the plan from self.owner.

        Clears `plan` and `unscheduled_tasks` first so repeated calls are idempotent.
        """
        self.plan = []
        self.unscheduled_tasks = []
        self.reasons = {}
        for task in self.owner.get_all_tasks():
            task.scheduled_start = task.scheduled_end = None

        due = [t for t in self.owner.get_all_tasks() if t.is_due_on(self.schedule_date)]
        windows = [(_minutes(s), _minutes(e)) for s, e in self.owner.effective_windows()]
        buffer = self.owner.buffer_minutes
        budget = self.owner.max_total_minutes
        busy: list[tuple[int, int]] = []

        def place(task: Task, start: int, why: str) -> None:
            task.scheduled_start = _to_time(start)
            task.scheduled_end = _to_time(start + task.duration_minutes)
            busy.append((start, start + task.duration_minutes))
            self.plan.append(task)
            self.reasons[task.task_id] = why

        def skip(task: Task, why: str) -> None:
            self.unscheduled_tasks.append(task)
            self.reasons[task.task_id] = why

        def over_budget(task: Task) -> bool:
            return budget is not None and self.total_duration + task.duration_minutes > budget

        pinned = [t for t in due if t.fixed_time and t.preferred_time is not None]
        flexible = [t for t in due if t not in pinned]

        for task in self.sort_by_priority(pinned):
            start = _minutes(task.preferred_time)  # type: ignore[arg-type]
            end = start + task.duration_minutes
            if over_budget(task):
                skip(task, "exceeds max_total_minutes")
            elif not any(ws <= start and end <= we for ws, we in windows):
                skip(task, "pinned time is outside available time")
            elif self._conflicts(start, end, busy, buffer):
                skip(task, "pinned time clashes with another task")
            else:
                place(task, start, "pinned at preferred time")

        for task in self.sort_by_priority(flexible):
            if over_budget(task):
                skip(task, "exceeds max_total_minutes")
                continue
            start = None
            why = f"{task.priority} priority, first open slot"
            if task.preferred_time is not None:
                start = self._find_slot(task.duration_minutes, windows, busy, buffer,
                                        _minutes(task.preferred_time))
                if start is not None:
                    why = f"{task.priority} priority, at/after preferred time"
            if start is None:
                start = self._find_slot(task.duration_minutes, windows, busy, buffer, 0)
            if start is None:
                skip(task, "no open slot long enough")
            else:
                place(task, start, why)

        self.plan = sort_by_time(self.plan)
        self.generated_at = datetime.now()

    @staticmethod
    def _conflicts(start: int, end: int, busy: list[tuple[int, int]], buffer: int) -> bool:
        """True if [start, end) is within `buffer` minutes of any busy span."""
        return any(start < b_end + buffer and end > b_start - buffer for b_start, b_end in busy)

    @classmethod
    def _find_slot(cls, duration: int, windows: list[tuple[int, int]],
                   busy: list[tuple[int, int]], buffer: int, earliest: int) -> Optional[int]:
        """Earliest start (in minutes) at or after `earliest` that fits, or None."""
        for ws, we in windows:
            start = max(ws, earliest)
            while start + duration <= we:
                end = start + duration
                clashes = [b for b in busy if start < b[1] + buffer and end > b[0] - buffer]
                if not clashes:
                    return start
                start = max(b[1] for b in clashes) + buffer
        return None

    def sort_by_priority(self, tasks: list[Task]) -> list[Task]:
        """Highest priority first; ties broken by shortest duration, then task_id."""
        return sorted(tasks, key=lambda t: (-t.priority_rank, t.duration_minutes, t.task_id))

    def complete_task(self, task_id: int, on: Optional[date] = None) -> Optional[Task]:
        """Complete a task by id (any pet); recurring tasks get their next instance added.

        `on` defaults to the schedule date. Returns the new task, or None.
        """
        for pet in self.owner.pets:
            if any(t.task_id == task_id for t in pet.tasks):
                return pet.complete_task(task_id, on or self.schedule_date)
        raise KeyError(f"No task with id {task_id}")

    def conflicts(self) -> list[tuple[Task, Task, str]]:
        """Overlaps in the current plan (including buffer), across all pets."""
        return detect_conflicts(self.plan, self.owner.buffer_minutes)

    def conflict_warnings(self, tasks: Optional[list[Task]] = None) -> list[str]:
        """Human-readable warnings for overlapping tasks; never raises.

        Checks `tasks` (default: the current plan), so hand-placed or edited
        tasks can be checked too. Same-pet and cross-pet clashes are labelled.
        Tasks without a start/end time are ignored.
        """
        try:
            pairs = detect_conflicts(self.plan if tasks is None else tasks,
                                     self.owner.buffer_minutes)
        except Exception as exc:  # a malformed task must not crash the app
            return [f"Could not check for conflicts: {exc}"]
        out = []
        for a, b, _ in pairs:
            pa, pb = self._pet_name(a), self._pet_name(b)
            who = (f"for {pa}" if a.pet_id == b.pet_id else f"between {pa} and {pb}")
            out.append(f"Conflict {who}: {pa} {a.task_type} "
                       f"({_fmt(a.scheduled_start)}-{_fmt(a.scheduled_end)}) overlaps "
                       f"{pb} {b.task_type} ({_fmt(b.scheduled_start)}-{_fmt(b.scheduled_end)})")
        return out

    def pinned_warnings(self) -> list[str]:
        """Explain pinned (fixed_time) tasks that could not be placed."""
        return [f"{self._pet_name(t)}: {t.task_type} pinned at {_fmt(t.preferred_time)} "
                f"was skipped - {self.reasons.get(t.task_id, '')}"
                for t in self.unscheduled_tasks if t.fixed_time]

    def suggest_slot(self, task: Task) -> Optional[time]:
        """Earliest free start for `task` around the current plan, or None."""
        windows = [(_minutes(s), _minutes(e)) for s, e in self.owner.effective_windows()]
        busy = [(_minutes(t.scheduled_start), _minutes(t.scheduled_end)) for t in self.plan]
        start = self._find_slot(task.duration_minutes, windows, busy,
                                self.owner.buffer_minutes, 0)
        return None if start is None else _to_time(start)

    def overload_minutes(self) -> int:
        """Minutes of due-task work beyond available time (0 if it all fits)."""
        avail = sum(_minutes(e) - _minutes(s) for s, e in self.owner.effective_windows())
        if self.owner.max_total_minutes is not None:
            avail = min(avail, self.owner.max_total_minutes)
        need = sum(t.duration_minutes for t in self.owner.get_all_tasks()
                   if t.is_due_on(self.schedule_date))
        return max(0, need - avail)

    def next_task(self, now: time) -> Optional[Task]:
        """First pending planned task starting at or after `now`."""
        return next((t for t in self.plan
                     if not t.completed and t.scheduled_start >= now), None)  # type: ignore[operator]

    def grouped_by_pet(self) -> list[list[Task]]:
        """Plan split into runs of consecutive tasks for the same pet."""
        runs: list[list[Task]] = []
        for t in self.plan:
            if runs and runs[-1][-1].pet_id == t.pet_id:
                runs[-1].append(t)
            else:
                runs.append([t])
        return runs

    def validate(self) -> bool:
        """Check no overlaps, all tasks inside windows, and max_total_minutes respected."""
        windows = self.owner.effective_windows()
        spans: list[tuple[int, int]] = []
        for t in self.plan:
            if t.scheduled_start is None or t.scheduled_end is None:
                return False
            if t.scheduled_start >= t.scheduled_end:
                return False
            if not any(ws <= t.scheduled_start and t.scheduled_end <= we for ws, we in windows):
                return False
            spans.append((_minutes(t.scheduled_start), _minutes(t.scheduled_end)))
        spans.sort()
        if any(spans[i][1] > spans[i + 1][0] for i in range(len(spans) - 1)):
            return False
        budget = self.owner.max_total_minutes
        return budget is None or self.total_duration <= budget

    def _pet_name(self, task: Task) -> str:
        """Return the name of the pet a task belongs to, or '?'."""
        pet = self.owner.get_pet(task.pet_id) if task.pet_id is not None else None
        return pet.pet_name if pet else "?"

    def explain_plan(self) -> str:
        """Return a readable plan listing each task's time slot and reason."""
        lines = [f"Plan for {self.owner.owner_name} on {self.schedule_date.isoformat()} "
                 f"({self.total_duration} min scheduled)"]
        for t in self.plan:
            lines.append(f"  {_fmt(t.scheduled_start)}-{_fmt(t.scheduled_end)}  "
                         f"{self._pet_name(t)}: {t.task_type}"
                         f"{' - ' + t.description if t.description else ''}"
                         f"  [{self.reasons.get(t.task_id, '')}]")
        over = self.overload_minutes()
        if over:
            lines.append(f"Warning: {over} min more work than available time.")
        lines.extend(f"Warning: {m}" for m in self.conflict_warnings())
        if self.unscheduled_tasks:
            lines.append("Skipped because:")
            for t in self.unscheduled_tasks:
                lines.append(f"  {self._pet_name(t)}: {t.task_type} "
                             f"({t.duration_minutes} min) - {self.reasons.get(t.task_id, '')}")
        return "\n".join(lines)

    def get_plan_for_pet(self, pet_id: int) -> list[Task]:
        """Return the scheduled tasks for one pet, in time order."""
        return [t for t in self.plan if t.pet_id == pet_id]

    def export_schedule(self, fmt: Literal["text", "json", "csv"] = "text") -> str:
        """Return the plan as text, JSON or CSV."""
        if fmt == "text":
            return self.explain_plan()
        rows = [{
            "pet": self._pet_name(t),
            "task": t.task_type,
            "description": t.description,
            "priority": t.priority,
            "start": _fmt(t.scheduled_start),
            "end": _fmt(t.scheduled_end),
        } for t in self.plan]
        if fmt == "json":
            return json.dumps({"date": self.schedule_date.isoformat(), "plan": rows}, indent=2)
        if fmt == "csv":
            buf = io.StringIO()
            writer = csv.DictWriter(
                buf, fieldnames=["pet", "task", "description", "priority", "start", "end"])
            writer.writeheader()
            writer.writerows(rows)
            return buf.getvalue()
        raise ValueError(f"Unknown export format: {fmt!r}")
