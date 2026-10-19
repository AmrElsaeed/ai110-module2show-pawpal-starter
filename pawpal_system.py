"""PawPal logic layer: backend classes for pet care scheduling (skeleton only)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
from enum import Enum
from itertools import count
from typing import Any, Literal, Optional

ExportFormat = Literal["text", "json", "csv"]

# Auto-generated ids so callers never have to manage them by hand.
_task_ids = count(1)
_pet_ids = count(1)
_owner_ids = count(1)
_schedule_ids = count(1)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TaskType(Enum):
    FEEDING = "feeding"
    WALK = "walk"
    MEDICATION = "medication"
    GROOMING = "grooming"
    PLAY = "play"
    VET_VISIT = "vet_visit"
    TRAINING = "training"


class Priority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class Frequency(Enum):
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


# ---------------------------------------------------------------------------
# Small value objects
# ---------------------------------------------------------------------------

@dataclass
class TimeSlot:
    """A same-day window. Does not cross midnight."""
    start: time
    end: time

    def __post_init__(self) -> None:
        if self.start >= self.end:
            raise ValueError(f"TimeSlot start {self.start} must be before end {self.end}")

    def duration_minutes(self) -> int:
        pass

    def overlaps(self, other: TimeSlot) -> bool:
        pass

    def contains(self, t: time) -> bool:
        pass


# ---------------------------------------------------------------------------
# Core data classes
# ---------------------------------------------------------------------------

@dataclass
class Task:
    """A care task. `pet_id` is set by Pet.add_task, not by the caller."""
    task_type: TaskType
    description: str = ""
    duration_minutes: int = 15
    priority: Priority = Priority.MEDIUM
    frequency: Frequency = Frequency.ONCE
    due_date: Optional[date] = None          # first/next date the task is due
    last_completed: Optional[date] = None
    preferred_time: Optional[time] = None
    # fixed_time=True: preferred_time is a hard pin, placed before everything else.
    # fixed_time=False: preferred_time is a soft hint the scheduler may move.
    fixed_time: bool = False
    task_id: int = field(default_factory=lambda: next(_task_ids))
    pet_id: Optional[int] = None

    @property
    def is_recurring(self) -> bool:
        return self.frequency is not Frequency.ONCE

    def is_due_on(self, day: date) -> bool:
        """True if this task belongs on `day`, based on frequency, due_date and last_completed."""
        pass

    def mark_complete(self, on: Optional[date] = None) -> None:
        """Record completion; for recurring tasks, advance due_date by `frequency`."""
        pass

    def is_urgent(self) -> bool:
        pass


@dataclass
class Pet:
    """Pet info (the 'Info' class in the UML). Owns its tasks."""
    pet_name: str
    species: str = ""
    breed: str = ""
    age: int = 0
    weight_kg: float = 0.0
    medical_notes: str = ""
    pet_id: int = field(default_factory=lambda: next(_pet_ids))
    owner_id: Optional[int] = None           # set by Owner.add_pet
    tasks: list[Task] = field(default_factory=list)

    def get_summary(self) -> str:
        pass

    def update_info(self, **changes: Any) -> None:
        """Update known fields only; raise AttributeError on unknown names."""
        pass

    def add_task(self, task: Task) -> None:
        """Append task and set task.pet_id = self.pet_id."""
        pass

    def remove_task(self, task_id: int) -> None:
        pass

    def tasks_due_on(self, day: date) -> list[Task]:
        pass


@dataclass
class Constraints:
    """Owner availability.

    Availability rule: `available_time` holds the real windows. `day_start` /
    `day_end` are only a fallback used when `available_time` is empty.
    `blocked_times` are always subtracted from whatever windows result.
    """
    available_time: list[TimeSlot] = field(default_factory=list)
    day_start: time = time(8, 0)
    day_end: time = time(20, 0)
    max_total_minutes: Optional[int] = None  # None = unlimited
    preferences: list[str] = field(default_factory=list)
    blocked_times: list[TimeSlot] = field(default_factory=list)
    buffer_minutes: int = 5                  # gap required between consecutive tasks

    def add_time_slot(self, slot: TimeSlot) -> None:
        pass

    def remove_time_slot(self, slot: TimeSlot) -> None:
        pass

    def effective_windows(self) -> list[TimeSlot]:
        """Resolve available_time / day_start-day_end fallback, minus blocked_times."""
        pass

    def is_available(self, t: time) -> bool:
        pass


@dataclass
class ScheduledItem:
    task: Task
    pet_id: int
    pet_name: str
    start_time: time
    end_time: time
    reason: str = ""


# ---------------------------------------------------------------------------
# Owner and scheduler
# ---------------------------------------------------------------------------

@dataclass
class Owner:
    owner_name: str
    email: str = ""
    owner_id: int = field(default_factory=lambda: next(_owner_ids))
    pets: list[Pet] = field(default_factory=list)
    constraints: Constraints = field(default_factory=Constraints)

    def add_pet(self, pet: Pet) -> None:
        """Append pet and set pet.owner_id = self.owner_id."""
        pass

    def remove_pet(self, pet_id: int) -> None:
        pass

    def get_pet(self, pet_id: int) -> Optional[Pet]:
        pass

    def get_all_tasks(self) -> list[Task]:
        """Flatten tasks from self.pets (pets are the single source of truth)."""
        pass


@dataclass
class GenerateSchedule:
    """Builds a one-day plan for an owner's pets.

    Intended algorithm:
      1. Collect tasks due on `schedule_date` (Owner.get_all_tasks + Task.is_due_on).
      2. Place `fixed_time` tasks at their pinned times; any that clash with
         blocked/unavailable time go to `unscheduled_tasks` with a reason.
      3. Sort the rest by priority (tie-break: shortest first), then place each
         in the first window with room, honoring `buffer_minutes` and
         `max_total_minutes`.
      4. Anything that doesn't fit goes to `unscheduled_tasks`.
    The scheduler never creates overlaps, so `validate` only double-checks.
    """
    owner: Owner
    schedule_date: date = field(default_factory=date.today)
    strategy: str = "priority"
    schedule_id: int = field(default_factory=lambda: next(_schedule_ids))
    items: list[ScheduledItem] = field(default_factory=list)
    unscheduled_tasks: list[Task] = field(default_factory=list)
    generated_at: Optional[datetime] = None

    @property
    def total_duration(self) -> int:
        return sum(i.task.duration_minutes for i in self.items)

    def generate(self) -> None:
        """Rebuild the plan from owner and owner.constraints.

        Clears `items` and `unscheduled_tasks` first so repeated calls are idempotent.
        """
        pass

    def sort_by_priority(self, tasks: list[Task]) -> list[Task]:
        pass

    def validate(self) -> bool:
        """Check no overlaps, all items inside windows, and max_total_minutes respected."""
        pass

    def explain_plan(self) -> str:
        pass

    def get_items_for_pet(self, pet_id: int) -> list[ScheduledItem]:
        pass

    def export_schedule(self, fmt: ExportFormat = "text") -> str:
        pass
