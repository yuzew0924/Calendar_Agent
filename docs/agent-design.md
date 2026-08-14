# Agent Design

## Purpose

The agent helps students turn messy course availability information into clear schedule options. It should behave like a planning assistant: extract structured course data, apply constraints, compare tradeoffs, and always show a visual calendar for each serious option.

## User Inputs

The agent should accept:

- Course names.
- Available sections and meeting times.
- Section status, such as open, closed, or unknown.
- Fixed selections that must be kept.
- Parsed preferences, such as earliest start time and preferred gap length.
- Scenario requests, such as comparing two possible course sets.

## Processing Pipeline

1. Normalize course and section data.
2. Validate the `ScheduleRequest` and its nested course groups.
3. Expand only the explicit course groups into combinations, selecting exactly
   one section from every declared group.
4. Apply fixed-section constraints.
5. Generate the Cartesian product across courses.
6. Reject options with time conflicts.
7. Apply hard preference constraints.
8. Score remaining options.
9. Return the best schedules with explanations.
10. Generate a weekly calendar visualization for every returned plan.

The solver represents these two product levels explicitly:

- `CourseCombination`: one selected section from every declared group in a
  single course.
- `ScheduleCandidate`: one course combination from every requested course.

Input order is retained at the course, group, and section levels so candidate
generation is deterministic.

## Scheduling Rules

Rules should be split into hard constraints and soft preferences.

Hard constraints:

- No overlapping meetings.
- Required fixed sections must be included.
- Required course components must be selected.
- Availability rules must be respected when the user asks to consider only open sections.

Soft preferences:

- Prefer later starts.
- Prefer compact class blocks.
- Prefer gaps of exactly 10 minutes or at least 2 hours.
- Penalize awkward gaps between 30 and 90 minutes.
- Prefer fewer campus trips.
- Prefer consistent daily patterns.

## Explanation Style

The agent should explain schedules in plain language:

- State whether the schedule works.
- Mention the strongest reason it is recommended.
- Call out any weakness, such as a risky closed section or an awkward gap.
- Include a calendar visualization every time a concrete schedule is discussed.

## Future Extensions

- Screenshot OCR for registration pages.
- UW Time Schedule import.
- Saved preference profiles.
- Seat availability refresh.
- Registration priority simulation.
- Export to Google Calendar or ICS.
## Scheduler Boundary

The FastAPI layer accepts validated `ScheduleRequest` values and serializes
responses. It does not own scheduling rules. The independent
`backend/app/scheduler/` package owns time normalization, section combination
generation, conflict filtering, scoring, and result explanations. This keeps
the core algorithm directly callable from tests and future non-HTTP workflows.
