# Course Schema and Validation

This document is the canonical Week 2 input contract. Public JSON uses
`camelCase`; Python attributes use `snake_case`. The implementation lives in
`backend/app/models.py`.

**Week 2 dates:** 2026-08-17 to 2026-08-23

**Goal:** Accurately represent different course structures through explicit
groups and reject invalid nested data before schedule generation.

## Request Shape

```text
ScheduleRequest
├── courses[]: Course
│   └── groups[]: SectionGroup
│       └── sections[]: Section
│           └── meetings[]: Meeting
└── preferences: Preferences
```

```json
{
  "courses": [
    {
      "code": "CSE 373",
      "groups": [
        {
          "type": "lecture",
          "choose": 1,
          "sections": [
            {
              "id": "A",
              "status": "open",
              "meetings": [
                {
                  "days": ["M", "W", "F"],
                  "startTime": "09:30",
                  "endTime": "10:20"
                }
              ]
            }
          ]
        }
      ]
    }
  ],
  "preferences": {
    "earliestStart": "09:30",
    "requireOpenSections": true,
    "fixedSections": {
      "CSE 373": ["A"]
    }
  }
}
```

Unknown fields are rejected. The `courses` array must contain at least one
course, and course codes must be unique within a request.

## Group-Driven Components

The `groups` array is the only source of course components. The backend does not
infer or add lecture, quiz, lab, or discussion groups.

- A lecture-only course contains only a `lecture` group.
- A lecture+lab course contains `lecture` and `lab` groups.
- A lecture+quiz+lab course contains all three groups.
- If no lab group is present, no lab is processed or generated.

A valid lecture-only structure:

```json
{
  "code": "CSE 373",
  "groups": [
    {
      "type": "lecture",
      "choose": 1,
      "sections": [
        {
          "id": "A",
          "status": "open",
          "meetings": []
        }
      ]
    }
  ]
}
```

A valid lecture+lab structure:

```json
{
  "code": "CHEM 142",
  "groups": [
    {
      "type": "lecture",
      "choose": 1,
      "sections": [
        {"id": "A", "status": "open", "meetings": []}
      ]
    },
    {
      "type": "lab",
      "choose": 1,
      "sections": [
        {"id": "AL", "status": "open", "meetings": []},
        {"id": "BL", "status": "open", "meetings": []}
      ]
    }
  ]
}
```

## Meeting

| JSON field | Python field | Type | Required | Validation |
|---|---|---|---|---|
| `days` | `days` | `DayCode[]` | Yes | Non-empty and unique |
| `startTime` | `start_time` | `HH:MM` | Yes | Strict 24-hour time |
| `endTime` | `end_time` | `HH:MM` | Yes | Strict 24-hour time and after start |
| `location` | `location` | `string \| null` | No | Defaults to `null` |

Day codes support exactly `M`, `T`, `W`, `Th`, and `F`. Full weekday names,
weekends, `TH`, and other variants are invalid. Every meeting must satisfy
`startTime < endTime`.

### Algorithm Normalization

`backend/app/scheduler/time_utils.py` is the canonical normalization path used
by models and scheduling algorithms. `backend/app/normalization.py` re-exports
the same functions for compatibility:

| Input | Normalized value |
|---|---|
| `M`, `T`, `W`, `Th`, `F` | Ordered `Weekday` values `0`, `1`, `2`, `3`, `4` |
| `09:30` | `570` minutes since midnight |
| `13:20` | `800` minutes since midnight |

`normalize_meeting()` expands a recurring Meeting into one
`NormalizedMeeting(weekday, start_minute, end_minute)` per day. Conflict and gap
logic must consume these numeric intervals rather than compare weekday or time
strings directly.

## Section

| JSON field | Python field | Type | Required | Validation |
|---|---|---|---|---|
| `id` | `id` | `string` | Yes | Uppercase letters and digits only; unique within course |
| `status` | `status` | `open \| closed \| unknown` | Yes | Enum value only |
| `sln` | `sln` | `string \| null` | No | Defaults to `null` |
| `meetings` | `meetings` | `Meeting[]` | Yes | May be empty |
| `requiredSectionIds` | `required_section_ids` | `string[]` | No | Defaults to `[]` |

Component type is not duplicated on a section. The containing group determines
whether the section is a lecture, quiz, lab, discussion, or other component.
`requiredSectionIds` may reference sections in another group of the same course;
unknown, same-group, self, and cyclic dependencies are rejected.

## SectionGroup

| JSON field | Python field | Type | Required | Validation |
|---|---|---|---|---|
| `type` | `type` | `lecture \| quiz \| lab \| discussion \| other` | Yes | Enum value only |
| `choose` | `choose` | `1` | No | Defaults to `1`; no other value is supported |
| `sections` | `sections` | `Section[]` | Yes | May be empty, producing zero combinations |

The generator selects exactly one section from every group explicitly present
in the course. It does not add missing quiz or lab groups. It also does not skip
an empty group: if a declared group has no sections, that course has zero valid
combinations and the complete request has zero schedules.

## Course

| JSON field | Python field | Type | Required | Validation |
|---|---|---|---|---|
| `code` | `code` | `string` | Yes | Non-empty; unique within request |
| `groups` | `groups` | `SectionGroup[]` | Yes | Non-empty; group types unique |
| `title` | `title` | `string \| null` | No | Non-empty when provided |

Section IDs must be unique across all groups in a course. The model preserves
the exact input groups and does not synthesize missing components.

## Preferences

`Preferences` is the validated model consumed by `ScheduleRequest` and the
scheduler. Forms may populate it directly. AI-generated values must reach it
only through the separate `ParsedPreferences` validation and conversion step.

| JSON field | Python field | Type | Default |
|---|---|---|---|
| `earliestStart` | `earliest_start` | `HH:MM \| null` | `null` |
| `allowEarlierIfOnlyOption` | `allow_earlier_if_only_option` | `boolean` | `false` |
| `allowedGapMinutes` | `allowed_gap_minutes` | `integer \| null` | `null` |
| `minimumLongGapMinutes` | `minimum_long_gap_minutes` | `integer \| null` | `null` |
| `requireOpenSections` | `require_open_sections` | `boolean` | `true` |
| `fixedSections` | `fixed_sections` | `object<string, string[]>` | `{}` |

Gap values must be non-negative. Every `fixedSections` key must match a course
`code` in the request, and every listed section ID must exist in that course. If
`requireOpenSections` is true, every fixed section must be `open`.

## AI ParsedPreferences

`ParsedPreferences` is the only accepted structured output from an AI
preference parser:

```json
{
  "earliestStart": "10:00",
  "earliestStartIsHard": true,
  "preferredDaysOff": ["F"],
  "fixedSections": ["CSE 373 A", "CSE 373 AA"],
  "requireOpenSections": true,
  "hardConstraints": ["Do not start before 10:00"],
  "softPreferences": ["Prefer compact schedules"]
}
```

| JSON field | Type | Default | Role |
|---|---|---|---|
| `earliestStart` | `HH:MM \| null` | `null` | Structured start-time preference |
| `earliestStartIsHard` | `boolean` | `false` | Marks earliest start as hard instead of soft |
| `preferredDaysOff` | `DayCode[]` | `[]` | Future ranking input only |
| `fixedSections` | `string[]` | `[]` | Hard filter after conversion |
| `requireOpenSections` | `boolean` | `true` | Hard filter after conversion |
| `hardConstraints` | `string[]` | `[]` | Explanation/provenance only; never executed directly |
| `softPreferences` | `string[]` | `[]` | Future ranking and explanation input |

Each fixed-section string must use `<course code> <section ID>`, such as
`CSE 373 A`. `earliestStartIsHard: true` requires `earliestStart`. Day codes
remain limited to `M`, `T`, `W`, `Th`, and `F`.

Calling `to_scheduler_preferences()` converts fixed-section references into
the scheduler map format, carries over open-only and earliest-start settings,
and sets `allowEarlierIfOnlyOption` from `earliestStartIsHard`. The backend does
not execute text from `hardConstraints` or `softPreferences`; a requirement
must be represented by a recognized structured field before it can affect
filtering.

Execution categories are explicit:

- Hard filtering inputs: `fixedSections`, `requireOpenSections`, and
  `earliestStart` when `earliestStartIsHard` is true.
- Soft ranking inputs: `preferredDaysOff` and a non-hard `earliestStart`.
- Non-filtering parser metadata: text in `hardConstraints` and
  `softPreferences`. These strings may support future ranking or explanations,
  but they cannot create scheduler rules without first being mapped to a
  recognized field.

### AI Course Context

Preference parsing includes a minimal catalog generated from the request's
validated courses. Each course contains only `courseCode`, `title`, and
flattened sections. Each section contains only `id`, group-derived `type`,
`status`, and meeting `days`, `startTime`, and `endTime`. Registration numbers,
locations, dependency IDs, and group configuration are not sent to the model.

The prompt may reference only courses and sections present in this catalog.
After `ParsedPreferences` validation, the backend converts the result to
`Preferences` and validates a new `ScheduleRequest` with the original courses.
This second pass rejects invented course codes, invented section IDs, and fixed
closed sections when `requireOpenSections` is true.

## ScheduleRequest

| JSON field | Type | Required | Validation |
|---|---|---|---|
| `courses` | `Course[]` | Yes | Non-empty; unique course codes |
| `preferences` | `Preferences` | No | Uses defaults when omitted |

All nested Meeting, Section, SectionGroup, Course, and Preferences
validators run when `ScheduleRequest` is parsed. Invalid nested data therefore
fails at the request boundary with a Pydantic/FastAPI validation error.

## Response Scaffold

The existing Week 3 response scaffold remains:

```json
{
  "schedules": [],
  "count": 0,
  "warnings": []
}
```

## Sample Data

`sample-data/courses.json` is the canonical development fixture. It contains:

- `CSE 373`: lecture only.
- `CHEM 142`: lecture + lab, selecting one lab from two.
- `BIOL 180`: lecture + quiz + lab.
- Valid open and closed section statuses.
- Valid weekday and `HH:MM` meeting values.

## Week 2 Completion Standard

Week 2 is complete when:

- Course, SectionGroup, Section, Meeting, ScheduleRequest, and Preferences
  models exist.
- Lecture-only, lecture+lab, and lecture+quiz+lab inputs validate.
- Missing groups are never automatically added.
- Every declared group requires exactly one selected section.
- Invalid weekdays, times, section IDs, statuses, dependencies, and fixed
  sections are rejected.
- README and sample request JSON parse through `ScheduleRequest`.
- `cd backend && pytest` passes all schema and validation tests.

Any contract change must update the models, README, this document, sample data,
and tests together.
