"""PawPal logic layer: backend classes for pet care scheduling (skeleton only)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
from enum import Enum
from typing import Any, Optional


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


# ---------------------------------------------------------------------------
# Small value objects
# ---------------------------------------------------------------------------

@dataclass
class TimeSlot:
    start: time
    end: time

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
    task_id: int
    pet_id: int
    task_type: TaskType
    description: str = ""
    duration_minutes: int = 15
    priority: Priority = Priority.MEDIUM
    is_recurring: bool = False
    frequency: str = ""
    preferred_time: Optional[time] = None
    completed: bool = False

    def mark_complete(self) -> None:
        pass

    def is_urgent(self) -> bool:
        pass


@dataclass
class Pet:
    """Pet info (the 'Info' class in the UML)."""
    pet_id: int
    owner_id: int
    pet_name: str
    species: str = ""
    breed: str = ""
    age: int = 0
    weight_kg: float = 0.0
    medical_notes: str = ""
    tasks: list[Task] = field(default_factory=list)

    def get_summary(self) -> str:
        pass

    def update_info(self, fields: dict[str, Any]) -> None:
        pass

    def add_task(self, task: Task) -> None:
        pass

    def remove_task(self, task_id: int) -> None:
        pass


@dataclass
class Constraints:
    owner_id: int
    available_time: list[TimeSlot] = field(default_factory=list)
    day_start: time = time(8, 0)
    day_end: time = time(20, 0)
    max_total_minutes: int = 0
    preferences: list[str] = field(default_factory=list)
    blocked_times: list[TimeSlot] = field(default_factory=list)
    buffer_minutes: int = 5

    def add_time_slot(self, slot: TimeSlot) -> None:
        pass

    def remove_time_slot(self, slot: TimeSlot) -> None:
        pass

    def is_available(self, t: time) -> bool:
        pass


@dataclass
class ScheduledItem:
    task: Task
    start_time: time
    end_time: time
    reason: str = ""


# ---------------------------------------------------------------------------
# Owner and scheduler
# ---------------------------------------------------------------------------

@dataclass
class Owner:
    owner_id: int
    owner_name: str
    email: str = ""
    pets: list[Pet] = field(default_factory=list)
    constraints: Optional[Constraints] = None

    def add_pet(self, pet: Pet) -> None:
        pass

    def remove_pet(self, pet_id: int) -> None:
        pass

    def get_all_tasks(self) -> list[Task]:
        pass


@dataclass
class GenerateSchedule:
    schedule_id: int
    owner_id: int
    schedule_date: date = field(default_factory=date.today)
    items: list[ScheduledItem] = field(default_factory=list)
    unscheduled_tasks: list[Task] = field(default_factory=list)
    total_duration: int = 0
    strategy: str = "priority"
    generated_at: Optional[datetime] = None

    def generate(self, owner: Owner, constraints: Constraints) -> None:
        pass

    def resolve_conflicts(self) -> None:
        pass

    def sort_by_priority(self) -> None:
        pass

    def validate(self) -> bool:
        pass

    def explain_plan(self) -> str:
        pass

    def get_items_for_pet(self, pet_id: int) -> list[ScheduledItem]:
        pass

    def export_schedule(self, format: str = "text") -> str:
        pass
