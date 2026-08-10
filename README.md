# Calendar Agent

Calendar Agent is a course schedule planning assistant. It takes course names, available lecture and section times, and personal scheduling preferences, then generates ranked schedule options with calendar-style visualizations.

## Goal

The project is designed for registration planning workflows where a student has several possible courses and sections, plus constraints such as:

- Avoid classes before a preferred start time.
- Prefer compact schedules.
- Avoid gaps shorter than a specified threshold.
- Allow only specific gap patterns, such as 10-minute transitions or 2-hour breaks.
- Keep fixed sections that have already been selected.
- Compare alternate course sets, such as `208 + 414 + 370 + 332` versus `351 + 414 + 370 + 332`.

## Core Workflow

1. Enter courses and available sections.
2. Mark fixed sections when a choice is already locked.
3. Configure preferences and hard constraints.
4. Generate valid schedule combinations.
5. Rank schedules by fit.
6. View each option as a weekly calendar.
7. Export or save preferred plans.

## Planned Directory Structure

```text
Calendar Agent/
├── README.md
├── docs/
│   ├── agent-design.md
│   └── input-format.md
├── src/
│   ├── app/
│   │   ├── index.html
│   │   ├── styles.css
│   │   └── main.js
│   ├── scheduler/
│   │   ├── solver.js
│   │   ├── scoring.js
│   │   └── time.js
│   └── data/
│       └── sample-courses.json
└── tests/
    └── scheduler.test.js
```

## Key Concepts

### Course

A course is a registration unit such as `CSE 332`, `CSE 414`, `INFO 370`, or `MATH 208`.

### Section

A section is one selectable class component, such as a lecture, quiz, lab, or discussion. A course may require one lecture and one linked quiz section.

### Schedule Option

A schedule option is one complete selection across all requested courses. It must be conflict-free and should satisfy the user's constraints.

### Preference

A preference affects ranking. Examples include avoiding early classes, minimizing short gaps, keeping Tuesdays free, or grouping classes into compact blocks.

### Hard Constraint

A hard constraint invalidates a schedule. Examples include time conflicts, unavailable sections when availability is required, or classes before an absolute earliest allowed time.

## Initial MVP Scope

The first version should support:

- Manual JSON input for courses and sections.
- Fixed and optional sections.
- Conflict detection across weekdays.
- Gap validation.
- Ranked schedule generation.
- Weekly calendar visualization.
- Multiple scenario comparison.

Image extraction and OCR can be added later as an input layer. The scheduler should stay independent from the OCR layer so manually entered data and parsed screenshot data use the same planning logic.

## Example Preference Profile

```json
{
  "earliestStart": "09:30",
  "allowEarlierIfOnlyOption": true,
  "allowedGapMinutes": [10],
  "minimumLongGapMinutes": 120,
  "preferCompactDays": true,
  "preferOpenMornings": true,
  "fixedSections": ["CSE 414 C", "CSE 414 CD"]
}
```

## Example Input Shape

```json
{
  "courses": [
    {
      "code": "CSE 414",
      "groups": [
        {
          "type": "lecture",
          "choose": 1,
          "sections": [
            {
              "id": "C",
              "status": "open",
              "meetings": [
                { "days": ["M", "W", "F"], "start": "12:30", "end": "13:20" }
              ]
            }
          ]
        },
        {
          "type": "quiz",
          "choose": 1,
          "sections": [
            {
              "id": "CD",
              "status": "open",
              "meetings": [
                { "days": ["Th"], "start": "14:30", "end": "15:20" }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

## Development Notes

The scheduler should be deterministic and explainable. Every generated option should include:

- Selected sections.
- Conflict status.
- Gap summary by day.
- Constraint violations, if any.
- A ranking score with readable reasons.

This makes the agent useful during real registration decisions because it can explain why one schedule is better than another.
