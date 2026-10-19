# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.
- What classes did you include, and what responsibilities did you assign to each?
core actions include: schuedlue meds, doctor appointments, enrichments. set priorities, preference and timing
Classes are Task, Pet, Constraints, ScheduledItem, Owner, GenerateSchedule, and a small TimeSlot

**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

My scheduler places tasks greedily: it sorts them by priority (shortest first on ties) and puts each one in the first open slot that fits, honoring the buffer between tasks. It never goes back and rearranges. The cost is that the plan isn't guaranteed to be the best possible. A high-priority 10-minute task that lands in the middle of a 60-minute window can split it into two small gaps, so a later 45-minute task is reported as "no open slot long enough" even though moving the first task would have fit both. A search-based approach (backtracking or optimal packing) could find that arrangement, but it is much more code and gets slow as tasks grow.

I think greedy is the right call here. A pet owner has a handful of tasks a day, and the rule is easy to explain: the most important things get placed first, and each task's "Why" note says so. Critical tasks like medication are never bumped by a lower-priority one, which matters more than squeezing in every last task. When something is skipped, the app says why and suggests the earliest free slot, so the owner can adjust by hand.

The conflict check makes a similar tradeoff. It is lightweight: it checks overlapping time ranges in a single sorted pass and returns warning messages instead of blocking or raising errors. When several tasks overlap, it compares each one only to the latest-ending earlier task, so it may report fewer pairs than exist. This is enough to tell the owner something is wrong without a full pairwise comparison.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
