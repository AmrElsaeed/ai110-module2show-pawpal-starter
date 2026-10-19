from datetime import date, datetime, time

import streamlit as st

from pawpal_system import Owner, Pet, Scheduler, Task, sort_by_time

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

# The session_state "vault": Streamlit reruns this whole script on every click,
# so only create the Owner if one isn't already stored. Otherwise we'd get a
# brand-new, empty Owner (and lose every pet and task) each time.
if "owner" not in st.session_state:
    st.session_state.owner = Owner(
        owner_name="Jordan",
        available_time=[(time(7, 0), time(9, 0)), (time(17, 0), time(20, 0))],
    )
owner: Owner = st.session_state.owner

st.title("🐾 PawPal+")
st.caption("Plan a day of pet care around your own free time.")

# ---------------------------------------------------------------- Owner
st.subheader("Owner & availability")
owner.owner_name = st.text_input("Owner name", value=owner.owner_name)

col1, col2 = st.columns(2)
with col1:
    owner.buffer_minutes = int(st.number_input(
        "Gap between tasks (min)", min_value=0, max_value=60, value=owner.buffer_minutes))
with col2:
    cap = st.number_input(
        "Max care minutes per day (0 = no limit)", min_value=0, max_value=1440,
        value=owner.max_total_minutes or 0)
    owner.max_total_minutes = int(cap) or None

st.markdown("**When are you free?**")
for window in list(owner.available_time):
    left, right = st.columns([4, 1])
    left.write(f"{window[0]:%H:%M} - {window[1]:%H:%M}")
    if right.button("Remove", key=f"rm_{window[0]}_{window[1]}"):
        owner.remove_time_slot(window)
        st.rerun()
if not owner.available_time:
    st.info(f"No windows set, so the default {owner.day_start:%H:%M}-{owner.day_end:%H:%M} is used.")

with st.form("add_window", clear_on_submit=False):
    c1, c2, c3 = st.columns([2, 2, 1])
    start = c1.time_input("From", value=time(12, 0))
    end = c2.time_input("To", value=time(13, 0))
    if c3.form_submit_button("Add window"):
        try:
            owner.add_time_slot((start, end))
            st.rerun()
        except ValueError as err:
            st.error(str(err))

st.divider()

# ----------------------------------------------------------------- Pets
st.subheader("Pets")
with st.form("add_pet", clear_on_submit=True):
    c1, c2, c3 = st.columns(3)
    pet_name = c1.text_input("Pet name")
    species = c2.selectbox("Species", ["dog", "cat", "other"])
    breed = c3.text_input("Breed")
    c4, c5 = st.columns(2)
    age = c4.number_input("Age (years)", min_value=0, max_value=40, value=1)
    weight = c5.number_input("Weight (kg)", min_value=0.0, max_value=200.0, value=5.0)
    if st.form_submit_button("Add pet"):
        if not pet_name.strip():
            st.error("Give your pet a name.")
        else:
            owner.add_pet(Pet(pet_name.strip(), species=species, breed=breed.strip(),
                              age=int(age), weight_kg=float(weight)))
            st.rerun()

if not owner.pets:
    st.info("No pets yet. Add one above.")
for pet in owner.pets:
    st.write(f"**{pet.get_summary()}**")

st.divider()

# ---------------------------------------------------------------- Tasks
st.subheader("Tasks")
if not owner.pets:
    st.caption("Add a pet first, then you can give it tasks.")
else:
    pets_by_id = {p.pet_id: p for p in owner.pets}
    with st.form("add_task", clear_on_submit=False):
        pet_id = st.selectbox("For which pet?", list(pets_by_id),
                              format_func=lambda i: pets_by_id[i].pet_name)
        c1, c2 = st.columns(2)
        task_type = c1.selectbox("Type", ["feeding", "walk", "medication", "grooming",
                                          "play", "vet_visit", "training"])
        description = c2.text_input("Description", value="Morning walk")
        c3, c4, c5 = st.columns(3)
        duration = c3.number_input("Duration (min)", min_value=1, max_value=240, value=20)
        priority = c4.selectbox("Priority", ["low", "medium", "high", "critical"], index=2)
        frequency = c5.selectbox("Repeats", ["once", "daily", "weekly", "monthly"], index=1)
        picked_days = st.multiselect("Only on these weekdays (optional, for repeating tasks)",
                                     DAY_NAMES)
        c6, c7, c8 = st.columns(3)
        use_time = c6.checkbox("Preferred time")
        pref = c7.time_input("Time", value=time(8, 0))
        fixed = c8.checkbox("Must be exactly then")
        if st.form_submit_button("Add task"):
            try:
                task = Task(task_type, description.strip(), int(duration), priority, frequency,
                            preferred_time=pref if use_time else None,
                            fixed_time=fixed and use_time,
                            weekdays={DAY_NAMES.index(d) for d in picked_days} or None)
                pets_by_id[pet_id].add_task(task)
                st.rerun()
            except ValueError as err:
                st.error(str(err))

    # Filter and sort controls (Owner.filter_tasks / sort_by_time).
    f1, f2, f3 = st.columns(3)
    pet_filter = f1.selectbox("Show pet", ["All pets"] + [p.pet_name for p in owner.pets])
    status_filter = f2.selectbox("Show status", ["All", "Pending", "Completed"])
    order = f3.selectbox("Order", ["As added", "By scheduled time"])
    shown = owner.filter_tasks(
        pet_name=None if pet_filter == "All pets" else pet_filter,
        completed={"All": None, "Pending": False, "Completed": True}[status_filter])
    if order == "By scheduled time":
        shown = sort_by_time(shown)
        st.caption("Scheduled times appear after you generate a schedule below.")

    if "flash" in st.session_state:
        st.success(st.session_state.pop("flash"))
    if not shown:
        st.info("No tasks match." if owner.get_all_tasks() else "No tasks yet. Add one above.")
    for t in shown:
        pet = pets_by_id[t.pet_id]
        when = (f"{t.scheduled_start:%H:%M}" if t.scheduled_start
                else f"~{t.preferred_time:%H:%M}" if t.preferred_time else "-")
        days = f" ({','.join(DAY_NAMES[d] for d in sorted(t.weekdays))})" if t.weekdays else ""
        left, right = st.columns([5, 1])
        left.write(f"**{pet.pet_name}** - {t.task_type}: {t.description or '(no description)'} "
                   f"| {t.duration_minutes} min | {t.priority} | repeats {t.frequency}{days} "
                   f"| {when}{' | pinned' if t.fixed_time else ''} "
                   f"| `{t.status(date.today())}`")
        if not t.completed and right.button("Complete", key=f"done_{t.task_id}"):
            nxt = pet.complete_task(t.task_id, date.today())
            st.session_state.flash = (
                f"Completed {t.task_type} for {pet.pet_name}."
                + (f" Next one is due {nxt.due_date:%a %b %d}." if nxt else ""))
            st.rerun()

st.divider()

# ------------------------------------------------------------- Schedule
st.subheader("Build schedule")
plan_day = st.date_input("Plan for", value=date.today())

if st.button("Generate schedule"):
    scheduler = Scheduler(owner, schedule_date=plan_day)
    scheduler.generate()
    st.session_state.scheduler = scheduler

def pet_label(task: Task) -> str:
    pet = owner.get_pet(task.pet_id)
    return pet.pet_name if pet else "?"


scheduler = st.session_state.get("scheduler")
if scheduler is not None:
    # Warnings: overload, skipped pinned tasks, overlapping tasks.
    over = scheduler.overload_minutes()
    if over:
        st.warning(f"There is {over} min more care work than available time.")
    for msg in scheduler.pinned_warnings():
        st.warning(msg)
    for msg in scheduler.conflict_warnings():
        st.warning(msg)

    if scheduler.plan:
        st.success(f"{len(scheduler.plan)} tasks scheduled, {scheduler.total_duration} minutes "
                   f"in total for {scheduler.schedule_date:%A, %B %d}.")
        up_next = scheduler.next_task(datetime.now().time())
        if up_next is not None and scheduler.schedule_date == date.today():
            st.info(f"Next up: {pet_label(up_next)} - {up_next.task_type} "
                    f"at {up_next.scheduled_start:%H:%M}")

        def plan_row(t: Task) -> dict:
            return {"Time": f"{t.scheduled_start:%H:%M}-{t.scheduled_end:%H:%M}",
                    "Pet": pet_label(t), "Task": t.task_type, "Description": t.description,
                    "Why": scheduler.reasons.get(t.task_id, "")}

        view = st.radio("View", ["Timeline", "Grouped by pet"], horizontal=True)
        if view == "Timeline":
            st.table([plan_row(t) for t in sort_by_time(scheduler.plan)])
        else:
            for run in scheduler.grouped_by_pet():
                st.markdown(f"**{pet_label(run[0])}**")
                st.table([plan_row(t) for t in run])

        # Manual move: conflicts are reported as warnings, never blocked.
        with st.expander("Move a task and check for conflicts"):
            by_id = {t.task_id: t for t in scheduler.plan}
            pick = st.selectbox("Task", list(by_id), format_func=lambda i: (
                f"{pet_label(by_id[i])} - {by_id[i].task_type} "
                f"({by_id[i].scheduled_start:%H:%M})"))
            new_start = st.time_input("New start", value=by_id[pick].scheduled_start)
            if st.button("Move"):
                task = by_id[pick]
                end_min = new_start.hour * 60 + new_start.minute + task.duration_minutes
                if end_min >= 24 * 60:
                    st.error("That would run past midnight.")
                else:
                    task.scheduled_start = new_start
                    task.scheduled_end = time(end_min // 60, end_min % 60)
                    scheduler.plan = sort_by_time(scheduler.plan)
                    st.rerun()
    else:
        st.warning("Nothing to schedule for that day.")

    if scheduler.unscheduled_tasks:
        st.error("Couldn't fit these in:")
        skipped = []
        for t in scheduler.unscheduled_tasks:
            slot = scheduler.suggest_slot(t)
            skipped.append({"Pet": pet_label(t), "Task": t.task_type,
                            "Min": t.duration_minutes,
                            "Reason": scheduler.reasons.get(t.task_id, ""),
                            "Earliest free slot": f"{slot:%H:%M}" if slot else "none"})
        st.table(skipped)

    with st.expander("Plain-text version"):
        st.code(scheduler.export_schedule("text"))
    d1, d2 = st.columns(2)
    d1.download_button("Download CSV", scheduler.export_schedule("csv"),
                       file_name="pawpal_schedule.csv", mime="text/csv")
    d2.download_button("Download JSON", scheduler.export_schedule("json"),
                       file_name="pawpal_schedule.json", mime="application/json")
