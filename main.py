"""Demo script: build an owner with two pets, add tasks, and print today's schedule."""

from datetime import date, time

from pawpal_system import Owner, Pet, Scheduler, Task, filter_tasks, sort_by_time


def main() -> None:
    owner = Owner(
        owner_name="Sam",
        email="sam@example.com",
        available_time=[(time(7, 0), time(9, 0)), (time(17, 0), time(20, 0))],
        blocked_times=[(time(8, 30), time(8, 45))],
    )

    rex = Pet("Rex", species="dog", breed="Labrador", age=4, weight_kg=30)
    mochi = Pet("Mochi", species="cat", breed="Siamese", age=2, weight_kg=4.2)
    owner.add_pet(rex)
    owner.add_pet(mochi)

    # Tasks are deliberately added out of time order.
    mochi.add_task(Task("play", "Feather wand", 15, "low"))
    rex.add_task(Task("training", "Sit and stay practice", 20, "medium",
                      preferred_time=time(17, 30)))
    mochi.add_task(Task("feeding", "Wet food", 10, "high", preferred_time=time(18, 0)))
    rex.add_task(Task("walk", "Morning walk", 30, "high", preferred_time=time(7, 30)))
    rex.add_task(Task("medication", "Joint supplement", 10, "critical",
                      preferred_time=time(7, 0), fixed_time=True))

    scheduler = Scheduler(owner, schedule_date=date.today())
    scheduler.generate()

    print("=" * 50)
    print(f"Today's Schedule - {date.today():%A, %B %d, %Y}")
    print(f"Owner: {owner.owner_name} | Pets: {', '.join(p.pet_name for p in owner.pets)}")
    print("=" * 50)
    print(scheduler.explain_plan())
    print("-" * 50)
    print(f"Valid plan: {scheduler.validate()}")

    def show(title: str, tasks: list[Task]) -> None:
        print(f"\n{title}")
        for t in tasks:
            pet = owner.get_pet(t.pet_id).pet_name
            print(f"  {_hhmm(t)}  {pet:<5} {t.task_type:<10} "
                  f"{'done' if t.completed else 'pending'}")

    def _hhmm(t: Task) -> str:
        return t.scheduled_start.strftime("%H:%M") if t.scheduled_start else "--:--"

    all_tasks = owner.get_all_tasks()
    show("Tasks in the order they were added:", all_tasks)
    show("Sorted by time (sort_by_time):", sort_by_time(all_tasks))

    # Complete one task so the status filter has something to show.
    rex.complete_task(rex.tasks[-1].task_id)  # medication
    show("Filter: pet_name='rex':", owner.filter_tasks(pet_name="rex"))
    show("Filter: pet_name='Mochi':", owner.filter_tasks(pet_name="Mochi"))
    show("Filter: completed=True:", owner.filter_tasks(completed=True))
    show("Filter: completed=False:", owner.filter_tasks(completed=False))
    show("Filter: Rex + pending, sorted by time:",
         sort_by_time(filter_tasks(all_tasks, owner, pet_name="Rex", completed=False)))
    show("Filter: unknown pet 'Ghost':", owner.filter_tasks(pet_name="Ghost"))

    # Conflict detection: hand-place two tasks at the exact same time (the scheduler
    # itself never does this), one pair for the same pet and one across pets.
    print("\nConflict check on the generated plan:", scheduler.conflict_warnings() or "none")
    bath = Task("grooming", "Bath", 20)
    laser = Task("play", "Laser pointer", 20)
    rex.add_task(bath)
    mochi.add_task(laser)
    bath.scheduled_start, bath.scheduled_end = time(17, 30), time(17, 50)   # same slot as Rex's training
    laser.scheduled_start, laser.scheduled_end = time(17, 30), time(17, 50)  # same slot, other pet
    print("After hand-placing two tasks at 17:30 alongside Rex's training:")
    warnings = scheduler.conflict_warnings(owner.get_all_tasks())
    for warning in warnings:
        print(f"  WARNING: {warning}")
    print(f"{len(warnings)} warning(s); program continued normally.")


if __name__ == "__main__":
    main()