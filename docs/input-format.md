# API Data Contract

This document is the canonical JSON contract for schedule generation. JSON field
names use `camelCase`. Future Python/Pydantic models should use `snake_case`
attributes with these JSON names as aliases.

## Object Relationships

```text
GenerateScheduleRequest
├── courses[]: Course
│   └── groups[]: SectionGroup
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

- Times use local 24-hour `HH:MM` strings.
- `start` must be earlier than `end`.
- Supported day codes are `M`, `T`, `W`, `Th`, and `F`.
- IDs are case-sensitive strings and must be unique within their documented scope.
- Required arrays may not be omitted. Arrays marked non-empty must contain at
  least one item.
- Optional nullable fields may be omitted or set to `null`.
- Unknown JSON fields should be rejected so input mistakes are visible.

## Meeting

A `Meeting` is one recurring time block for a section. A section with different
times on different days uses multiple meetings.

| JSON field | Python field | Type | Required | Rules |
|---|---|---|---|---|
| `days` | `days` | `DayCode[]` | Yes | Non-empty; no duplicate days |
| `start` | `start` | `time` as `HH:MM` | Yes | Must be before `end` |
| `end` | `end` | `time` as `HH:MM` | Yes | Must be after `start` |
| `location` | `location` | `string \| null` | No | Defaults to `null` |

```json
{
  "days": ["M", "W", "F"],
  "start": "12:30",
  "end": "13:20",
  "location": "EEB 125"
}
```

## Section

A `Section` is one selectable lecture, quiz, lab, or discussion section.

| JSON field | Python field | Type | Required | Rules |
|---|---|---|---|---|
| `id` | `id` | `string` | Yes | Non-empty; unique within a course |
| `status` | `status` | `open \| closed \| unknown` | Yes | Availability at input time |
| `meetings` | `meetings` | `Meeting[]` | Yes | Non-empty for the weekday MVP |
| `sln` | `sln` | `string \| null` | No | Registration identifier; defaults to `null` |
| `requiredSectionIds` | `required_section_ids` | `string[]` | No | Defaults to `[]`; every referenced section must also be selected |

`requiredSectionIds` captures linked-section rules without relying on section-name
patterns. For example, quiz `CD` can require lecture `C`. Every referenced ID
must exist in another group of the same course. Cyclic dependencies are invalid.

```json
{
  "id": "CD",
  "status": "open",
  "sln": "13231",
  "requiredSectionIds": ["C"],
  "meetings": [
    {
      "days": ["Th"],
      "start": "14:30",
      "end": "15:20",
      "location": null
    }
  ]
}
```

## SectionGroup

A `SectionGroup` describes one course component and how many sections must be
selected from it.

| JSON field | Python field | Type | Required | Rules |
|---|---|---|---|---|
| `id` | `id` | `string` | Yes | Stable ID unique within the course |
| `type` | `type` | `lecture \| quiz \| lab \| discussion \| other` | Yes | Component category |
| `choose` | `choose` | `integer` | Yes | At least `1`; no greater than section count |
| `sections` | `sections` | `Section[]` | Yes | Non-empty |
| `name` | `name` | `string \| null` | No | Display label; defaults to `null` |

```json
{
  "id": "quiz",
  "type": "quiz",
  "choose": 1,
  "sections": [
    {
      "id": "BA",
      "status": "open",
      "meetings": [
        {
          "days": ["Th"],
          "start": "13:30",
          "end": "14:20"
        }
      ]
    }
  ]
}
```

## Course

A `Course` contains every candidate component and section for one requested
course.

| JSON field | Python field | Type | Required | Rules |
|---|---|---|---|---|
| `code` | `code` | `string` | Yes | Non-empty; unique within the request |
| `groups` | `groups` | `SectionGroup[]` | Yes | Non-empty |
| `title` | `title` | `string \| null` | No | Display name; defaults to `null` |

All section IDs must be unique across the course, even when they belong to
different groups. This makes fixed selections and dependencies unambiguous.

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
| `fixedSections` | `fixed_sections` | `string[]` | `[]` | Canonical `COURSE_CODE SECTION_ID` values that every option must include |

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

```json
{
  "courses": [
    {
      "code": "CSE 414",
      "title": "Database Systems",
      "groups": [
        {
          "id": "lecture",
          "type": "lecture",
          "choose": 1,
          "sections": [
            {
              "id": "C",
              "status": "open",
              "meetings": [
                {
                  "days": ["M", "W", "F"],
                  "start": "12:30",
                  "end": "13:20"
                }
              ]
            }
          ]
        },
        {
          "id": "quiz",
          "type": "quiz",
          "choose": 1,
          "sections": [
            {
              "id": "CD",
              "status": "open",
              "requiredSectionIds": ["C"],
              "meetings": [
                {
                  "days": ["Th"],
                  "start": "14:30",
                  "end": "15:20"
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
    "allowEarlierIfOnlyOption": true,
    "allowedGapMinutes": [10],
    "minimumLongGapMinutes": 120,
    "requireOpenSections": true,
    "fixedSections": ["CSE 414 C", "CSE 414 CD"]
  },
  "maxResults": 10
}
```

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

Each response-only `SelectedSection` contains required `courseCode`, `groupId`,
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
          "groupId": "lecture",
          "section": {
            "id": "C",
            "status": "open",
            "meetings": [
              {
                "days": ["M", "W", "F"],
                "start": "12:30",
                "end": "13:20"
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
invalid or contradictory requests should use FastAPI's HTTP `422` validation
response rather than `GenerateScheduleResponse`.
