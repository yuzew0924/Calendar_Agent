# API Data Contract

This document is the canonical JSON contract for schedule generation. JSON field
names use `camelCase`. The Pydantic models in `backend/app/models.py` use
`snake_case` attributes with these JSON names as aliases.

## Object Relationships

```text
GenerateScheduleRequest
├── courses[]: Course
│   └── sectionGroups[]: SectionGroup
│       └── sections[]: Section
│           └── meetings[]: Meeting
└── preferences: Preferences

GenerateScheduleResponse
└── options[]
    └── selections[]
        └── section: Section
```

A request contains every course the user wants in one generated schedule. Each
course code must be unique within the request. For every `SectionGroup`, the
generator selects exactly `choose` sections. It then combines those selections
across courses, enforces section dependencies and fixed sections, rejects time
conflicts, and ranks the remaining schedules.

## Shared Conventions

- Times use strict local 24-hour `HH:MM` strings.
- `startTime` must be earlier than `endTime`.
- Supported day codes are `M`, `T`, `W`, `Th`, and `F`.
- IDs are case-sensitive strings and must be unique within their documented scope.
- Required arrays may not be omitted, but `meetings` and `sections` may be empty.
- Optional nullable fields may be omitted or set to `null`.
- Unknown JSON fields are rejected so input mistakes are visible.

## Meeting

A `Meeting` is one recurring time block for a section. A section with different
times on different days uses multiple meetings.

| JSON field | Python field | Type | Required | Rules |
|---|---|---|---|---|
| `days` | `days` | `DayCode[]` | Yes | Non-empty; no duplicate days |
| `startTime` | `start_time` | `time` as `HH:MM` | Yes | Must be before `endTime` |
| `endTime` | `end_time` | `time` as `HH:MM` | Yes | Must be after `startTime` |
| `location` | `location` | `string \| null` | No | Defaults to `null` |

```json
{
  "days": ["M", "W", "F"],
  "startTime": "09:30",
  "endTime": "10:20",
  "location": "KNE 120"
}
```

## Section

A `Section` is one selectable lecture, quiz, lab, or discussion section.

| JSON field | Python field | Type | Required | Rules |
|---|---|---|---|---|
| `id` | `id` | `string` | Yes | Non-empty; unique within a course |
| `type` | `type` | `lecture \| quiz \| lab \| discussion \| other` | Yes | Must match its group type |
| `status` | `status` | `open \| closed \| unknown` | Yes | Availability at input time |
| `sln` | `sln` | `string \| null` | No | Registration identifier; defaults to `null` |
| `meetings` | `meetings` | `Meeting[]` | Yes | May be empty for an unscheduled or asynchronous section |
| `requiredSectionIds` | `required_section_ids` | `string[]` | No | Defaults to `[]`; referenced sections must also be selected |

`requiredSectionIds` captures linked-section rules without relying on section-name
patterns. For example, quiz `CD` can require lecture `C`. Every referenced ID
must exist in another group of the same course. Cyclic dependencies are invalid.

```json
{
  "id": "AA",
  "type": "quiz",
  "status": "open",
  "sln": "12345",
  "requiredSectionIds": ["A"],
  "meetings": [
    {
      "days": ["Th"],
      "startTime": "09:30",
      "endTime": "10:20",
      "location": "LOW 101"
    }
  ]
}
```

## SectionGroup

A `SectionGroup` contains sections of one type and defines how many must be
selected.

| JSON field | Python field | Type | Required | Rules |
|---|---|---|---|---|
| `type` | `type` | `lecture \| quiz \| lab \| discussion \| other` | Yes | Must match every contained section |
| `choose` | `choose` | `integer` | Yes | At least `0`; no greater than section count |
| `sections` | `sections` | `Section[]` | Yes | May be empty only when `choose` is `0` |

```json
{
  "type": "quiz",
  "choose": 1,
  "sections": [
    {
      "id": "AA",
      "type": "quiz",
      "status": "open",
      "sln": "12345",
      "meetings": []
    }
  ]
}
```

## Course

A `Course` contains every candidate section group for one requested course.

| JSON field | Python field | Type | Required | Rules |
|---|---|---|---|---|
| `courseCode` | `course_code` | `string` | Yes | Non-empty; unique within the request |
| `title` | `title` | `string` | Yes | Non-empty display name |
| `sectionGroups` | `section_groups` | `SectionGroup[]` | Yes | Non-empty; group types must be unique |

All section IDs must be unique across a course. This makes fixed selections and
section dependencies unambiguous.

```json
{
  "courseCode": "CSE 123",
  "title": "Computer Programming III",
  "sectionGroups": [
    {
      "type": "lecture",
      "choose": 0,
      "sections": []
    },
    {
      "type": "quiz",
      "choose": 0,
      "sections": []
    }
  ]
}
```

## Preferences

Every preference field is optional. Omitting `preferences` from the request uses
all defaults shown below.

| JSON field | Python field | Type | Default | Meaning |
|---|---|---|---|---|
| `earliestStart` | `earliest_start` | `HH:MM \| null` | `null` | Preferred earliest class start; disabled when `null` |
| `allowEarlierIfOnlyOption` | `allow_earlier_if_only_option` | `boolean` | `false` | Permit earlier classes only when no schedule satisfies `earliestStart` |
| `allowedGapMinutes` | `allowed_gap_minutes` | `integer[]` | `[]` | Exact short gaps that receive no penalty |
| `minimumLongGapMinutes` | `minimum_long_gap_minutes` | `integer \| null` | `null` | Gaps at or above this value receive no penalty |
| `requireOpenSections` | `require_open_sections` | `boolean` | `true` | Exclude `closed` and `unknown` sections when true |
| `fixedSections` | `fixed_sections` | `string[]` | `[]` | Canonical `COURSE_CODE SECTION_ID` values every option must include |

Preference rules:

- Gap values are non-negative minutes and may not contain duplicates.
- When `earliestStart` is set and `allowEarlierIfOnlyOption` is `false`, the
  earliest time is a hard constraint.
- When `allowEarlierIfOnlyOption` is `true`, schedules meeting `earliestStart`
  are considered first; earlier schedules are considered only if none exist.
- A gap is preferred when it exactly matches an `allowedGapMinutes` value or is
  at least `minimumLongGapMinutes`. Other gaps receive a ranking penalty.
- A fixed section must exist in the named course. A fixed non-open section is
  incompatible with `requireOpenSections: true` and makes the request invalid.

## GenerateScheduleRequest

| JSON field | Python field | Type | Required | Rules |
|---|---|---|---|---|
| `courses` | `courses` | `Course[]` | Yes | Non-empty; unique course codes |
| `preferences` | `preferences` | `Preferences` | No | Defaults to an empty/default preferences object |
| `maxResults` | `max_results` | `integer` | No | Defaults to `10`; range `1` to `100` |

The complete request example is maintained in `README.md` and
`sample-data/courses.json`.

## GenerateScheduleResponse

The response is self-contained: each selected section includes its meetings so
the frontend can render a calendar without joining against the request.

| JSON field | Python field | Type | Required | Rules |
|---|---|---|---|---|
| `options` | `options` | `ScheduleOption[]` | Yes | Ranked best-first; may be empty |
| `totalOptions` | `total_options` | `integer` | Yes | Total valid options before `maxResults` truncation |
| `warnings` | `warnings` | `string[]` | No | Defaults to `[]`; request-level notices |

Each response-only `ScheduleOption` contains:

| Field | Type | Required | Meaning |
|---|---|---|---|
| `id` | `string` | Yes | Stable option identifier within the response |
| `rank` | `integer` | Yes | One-based rank |
| `score` | `number` | Yes | Normalized score from `0` to `100` |
| `selections` | `SelectedSection[]` | Yes | One record per selected section |
| `reasons` | `string[]` | No | Defaults to `[]`; positive ranking explanations |
| `warnings` | `string[]` | No | Defaults to `[]`; option-specific tradeoffs |

Each response-only `SelectedSection` contains required `courseCode`, `groupType`,
and `section` fields. `section` uses the same `Section` contract defined above.

```json
{
  "options": [
    {
      "id": "option-1",
      "rank": 1,
      "score": 94,
      "selections": [
        {
          "courseCode": "CSE 414",
          "groupType": "lecture",
          "section": {
            "id": "C",
            "type": "lecture",
            "status": "open",
            "meetings": [
              {
                "days": ["M", "W", "F"],
                "startTime": "12:30",
                "endTime": "13:20"
              }
            ]
          }
        }
      ],
      "reasons": ["No conflicts", "Short gaps"],
      "warnings": []
    }
  ],
  "totalOptions": 1,
  "warnings": []
}
```

An empty successful result uses `options: []` and `totalOptions: 0`. Structurally
invalid or contradictory requests use FastAPI's HTTP `422` validation response.
