from datetime import date

from pawpal_system import Pet, Task


def test_mark_complete_changes_task_status():
    task = Task("feeding", "Breakfast")
    assert task.completed is False

    task.mark_complete(on=date(2026, 10, 18))

    assert task.completed is True
    assert task.last_completed == date(2026, 10, 18)


def test_adding_task_increases_pet_task_count():
    pet = Pet("Rex", species="dog")
    assert len(pet.tasks) == 0

    pet.add_task(Task("walk", "Morning walk"))
    assert len(pet.tasks) == 1

    pet.add_task(Task("feeding", "Dinner"))
    assert len(pet.tasks) == 2


# ---- sorting, filtering, recurrence, conflicts ----
from datetime import time

import pytest

from pawpal_system import (Owner, Scheduler, _add_months, detect_conflicts,
                           filter_tasks, insert_by_time, sort_by_time)


def _placed(kind, start, end, prio="medium"):
    t = Task(kind, priority=prio)
    t.scheduled_start, t.scheduled_end = start, end
    return t


def test_sort_by_time_puts_unscheduled_last_and_breaks_ties_by_priority():
    a = _placed("walk", time(9, 0), time(9, 30), "low")
    b = _placed("feeding", time(9, 0), time(9, 10), "high")
    c = Task("play")
    assert sort_by_time([c, a, b]) == [b, a, c]
    assert sort_by_time([]) == []


def test_insert_by_time_keeps_order():
    plan = [_placed("a", time(8, 0), time(8, 5)), _placed("c", time(10, 0), time(10, 5))]
    mid = _placed("b", time(9, 0), time(9, 5))
    insert_by_time(plan, mid)
    assert plan[1] is mid


def test_filter_by_pet_status_and_unknown_pet():
    owner = Owner("Sam")
    rex, mochi = Pet("Rex"), Pet("Mochi")
    owner.add_pet(rex)
    owner.add_pet(mochi)
    t1, t2 = Task("walk"), Task("feeding")
    rex.add_task(t1)
    mochi.add_task(t2)
    t2.mark_complete(on=date(2026, 1, 1))
    tasks = owner.get_all_tasks()
    assert filter_tasks(tasks, owner, pet_name="REX") == [t1]
    assert filter_tasks(tasks, completed=True) == [t2]
    assert filter_tasks(tasks, owner, pet_name="Nobody") == []
    assert filter_tasks(tasks) == tasks


def test_status_overdue():
    t = Task("walk", due_date=date(2026, 1, 1))
    assert t.status(date(2026, 1, 2)) == "overdue"
    assert t.status(date(2026, 1, 1)) == "pending"


def test_complete_task_spawns_next_daily_occurrence():
    pet = Pet("Rex")
    t = Task("feeding", frequency="daily")
    pet.add_task(t)
    nxt = pet.complete_task(t.task_id, on=date(2026, 10, 18))
    assert t.completed and nxt is not None and nxt.task_id != t.task_id
    assert nxt.due_date == date(2026, 10, 19) and not nxt.completed
    assert len(pet.tasks) == 2
    assert pet.complete_task(nxt.task_id, on=date(2026, 10, 25)).due_date == date(2026, 10, 26)


def test_complete_one_off_spawns_nothing():
    pet = Pet("Rex")
    t = Task("vet_visit")
    pet.add_task(t)
    assert pet.complete_task(t.task_id) is None
    with pytest.raises(KeyError):
        pet.complete_task(9999999)


def test_monthly_clamps_to_month_end():
    assert _add_months(date(2026, 1, 31)) == date(2026, 2, 28)
    assert _add_months(date(2026, 12, 15)) == date(2027, 1, 15)
    t = Task("grooming", frequency="monthly")
    assert t.mark_complete(on=date(2026, 1, 31)).due_date == date(2026, 2, 28)


def test_weekday_recurrence():
    t = Task("walk", frequency="weekly", weekdays={0, 2, 4})
    assert t.is_due_on(date(2026, 10, 19))       # Monday
    assert not t.is_due_on(date(2026, 10, 20))   # Tuesday
    assert t.next_due_after(date(2026, 10, 19)) == date(2026, 10, 21)
    with pytest.raises(ValueError):
        Task("walk", frequency="weekly", weekdays={7})


def test_detect_conflicts_overlap_touching_and_long_task():
    long = _placed("walk", time(9, 0), time(11, 0))
    a = _placed("feeding", time(9, 30), time(9, 40))
    b = _placed("play", time(10, 0), time(10, 10))
    touch = _placed("grooming", time(11, 0), time(11, 10))
    found = detect_conflicts([touch, b, a, long])
    assert [(x, y) for x, y, _ in found] == [(long, a), (long, b)]
    assert detect_conflicts([long, touch]) == []
    assert detect_conflicts([long, touch], buffer=5) != []
    assert detect_conflicts([]) == []


def test_scheduler_warnings_and_helpers():
    owner = Owner("Sam", available_time=[(time(7, 0), time(8, 0))], buffer_minutes=0)
    pet = Pet("Rex")
    owner.add_pet(pet)
    pet.add_task(Task("medication", duration_minutes=10, priority="critical",
                      preferred_time=time(6, 0), fixed_time=True))
    pet.add_task(Task("walk", duration_minutes=45))
    pet.add_task(Task("training", duration_minutes=45))
    s = Scheduler(owner, schedule_date=date(2026, 10, 18))
    s.generate()
    assert s.validate() and s.conflicts() == []
    assert s.overload_minutes() == 40          # 100 min of work, 60 available
    assert any("pinned" in w for w in s.pinned_warnings())
    assert "Warning: 40 min" in s.explain_plan()
    assert s.next_task(time(0, 0)) is s.plan[0]
    assert len(s.grouped_by_pet()) == 1
    assert s.suggest_slot(Task("play", duration_minutes=10)) == time(7, 45)
    assert s.suggest_slot(Task("play", duration_minutes=30)) is None


def test_owner_filter_tasks_method():
    owner = Owner("Sam")
    rex, mochi = Pet("Rex"), Pet("Mochi")
    owner.add_pet(rex)
    owner.add_pet(mochi)
    a, b, c = Task("walk"), Task("feeding"), Task("play")
    rex.add_task(a)
    rex.add_task(b)
    mochi.add_task(c)
    b.mark_complete(on=date(2026, 1, 1))
    assert owner.filter_tasks() == [a, b, c]
    assert owner.filter_tasks(pet_name="rex") == [a, b]
    assert owner.filter_tasks(completed=True) == [b]
    assert owner.filter_tasks(pet_name="Rex", completed=False) == [a]
    assert owner.filter_tasks(pet_name="Ghost") == []


def test_mark_complete_returns_next_occurrence_for_daily_and_weekly():
    daily = Task("feeding", frequency="daily")
    nxt = daily.mark_complete(on=date(2026, 10, 18))
    assert daily.completed and not nxt.completed
    assert nxt.due_date == date(2026, 10, 19) and nxt.task_id != daily.task_id
    weekly = Task("grooming", frequency="weekly")
    assert weekly.mark_complete(on=date(2026, 10, 18)).due_date == date(2026, 10, 25)
    assert Task("vet_visit").mark_complete() is None


def test_scheduler_complete_task_adds_next_instance_to_right_pet():
    owner = Owner("Sam")
    rex, mochi = Pet("Rex"), Pet("Mochi")
    owner.add_pet(rex)
    owner.add_pet(mochi)
    t = Task("feeding", frequency="daily")
    mochi.add_task(t)
    s = Scheduler(owner, schedule_date=date(2026, 10, 18))
    nxt = s.complete_task(t.task_id)
    assert nxt in mochi.tasks and nxt not in rex.tasks and nxt.pet_id == mochi.pet_id
    assert nxt.due_date == date(2026, 10, 19)
    assert not nxt.is_due_on(date(2026, 10, 18)) and nxt.is_due_on(date(2026, 10, 19))
    with pytest.raises(KeyError):
        s.complete_task(9999999)


def test_conflict_warnings_same_pet_and_cross_pet_without_raising():
    owner = Owner("Sam", buffer_minutes=0)
    rex, mochi = Pet("Rex"), Pet("Mochi")
    owner.add_pet(rex)
    owner.add_pet(mochi)
    a, b, c = Task("walk"), Task("grooming"), Task("play")
    rex.add_task(a)
    rex.add_task(b)
    mochi.add_task(c)
    a.scheduled_start, a.scheduled_end = time(7, 0), time(7, 30)
    b.scheduled_start, b.scheduled_end = time(7, 15), time(7, 45)   # same pet as a
    c.scheduled_start, c.scheduled_end = time(7, 40), time(8, 0)    # other pet, overlaps b
    s = Scheduler(owner)
    warnings = s.conflict_warnings(owner.get_all_tasks())
    assert len(warnings) == 2
    assert "for Rex" in warnings[0] and "between Rex and Mochi" in warnings[1]
    assert s.conflict_warnings([]) == []
    assert s.conflict_warnings([Task("walk")]) == []        # unscheduled: ignored
    assert s.conflict_warnings() == []                      # empty plan


def test_generated_plan_has_no_conflict_warnings():
    owner = Owner("Sam", available_time=[(time(7, 0), time(9, 0))])
    pet = Pet("Rex")
    owner.add_pet(pet)
    pet.add_task(Task("walk", duration_minutes=30))
    pet.add_task(Task("feeding", duration_minutes=10))
    s = Scheduler(owner, schedule_date=date(2026, 10, 18))
    s.generate()
    assert s.conflict_warnings() == []
