"""Demo script: build an owner with two pets, add tasks, and print today's schedule."""

from datetime import date, time

from pawpal_system import Owner, Pet, Scheduler, Task


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

    rex.add_task(Task("medication", "Joint supplement", 10, "critical",
                      preferred_time=time(7, 0), fixed_time=True))
    rex.add_task(Task("walk", "Morning walk", 30, "high", preferred_time=time(7, 30)))
    rex.add_task(Task("training", "Sit and stay practice", 20, "medium",
                      preferred_time=time(17, 30)))
    mochi.add_task(Task("feeding", "Wet food", 10, "high", preferred_time=time(18, 0)))
    mochi.add_task(Task("play", "Feather wand", 15, "low"))

    scheduler = Scheduler(owner, schedule_date=date.today())
    scheduler.generate()

    print("=" * 50)
    print(f"Today's Schedule - {date.today():%A, %B %d, %Y}")
    print(f"Owner: {owner.owner_name} | Pets: {', '.join(p.pet_name for p in owner.pets)}")
    print("=" * 50)
    print(scheduler.explain_plan())
    print("-" * 50)
    print(f"Valid plan: {scheduler.validate()}")


if __name__ == "__main__":
    main()
