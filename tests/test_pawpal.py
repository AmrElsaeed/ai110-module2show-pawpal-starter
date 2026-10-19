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
