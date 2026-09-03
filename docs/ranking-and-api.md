# Schedule Ranking and Generation API

## Endpoint

`POST /api/schedules/generate` returns at most `topN` legal schedules. The
request must contain `courses`, `topN` from 1 through 50, and exactly one
preference source:

- `preferenceText`: parsed through the validated AI preference pipeline.
- `preferences`: an already parsed `ParsedPreferences` object.

`enhanceReasons` is optional and defaults to `true`. It controls only reason
wording. It cannot affect candidate generation, scores, or ranks.

## Response

```json
{
  "interpretedPreferences": {
    "earliestStart": "11:00",
    "earliestStartIsHard": false,
    "preferredDaysOff": ["F"],
    "requiredDaysOff": [],
    "preferredTimeOfDay": "afternoon",
    "fixedSections": ["CSE 373 A"],
    "requireOpenSections": true,
    "hardConstraints": ["Fixed section: CSE 373 A"],
    "softPreferences": ["Prefer Friday off"],
    "conflicts": [],
    "needsClarification": false,
    "clarificationQuestions": []
  },
  "schedules": [
    {
      "rank": 1,
      "score": 94,
      "sections": [
        {
          "courseCode": "CSE 373",
          "groupType": "lecture",
          "sectionId": "A",
          "status": "open",
          "sln": null,
          "meetings": [
            {
              "days": ["M", "W", "F"],
              "startTime": "11:30",
              "endTime": "12:20",
              "location": null
            }
          ]
        }
      ],
      "scoreBreakdown": {
        "earliestStart": {
          "score": 25,
          "maximum": 25,
          "details": "All class days start at or after 11:00",
          "affectedSections": []
        }
      },
      "reasons": ["Includes required section CSE 373 A"],
      "tradeoffs": []
    }
  ],
  "count": 1,
  "warnings": []
}
```

The real `scoreBreakdown` always contains all four scoring categories below.
The abbreviated example shows one category for readability.

## Deterministic Scoring

Scores range from 0 to 100 and do not use AI:

| Rule | Maximum | Behavior |
|---|---:|---|
| `earliestStart` | 25 | Penalizes each class day's first meeting before the preferred time; the penalty is halved when earlier classes are allowed as fallback |
| `preferredTimeOfDay` | 20 | Awards points by the proportion of weekly meetings in morning, afternoon, or evening |
| `gaps` | 30 | Combines compactness with penalties for 30-90 minute fragmented gaps and total idle time |
| `preferredDaysOff` | 25 | Awards points by the proportion of preferred days that remain free |

Time-of-day buckets use meeting start time:

- Morning: before 12:00.
- Afternoon: 12:00 through 16:59.
- Evening: 17:00 or later.
- None: neutral and does not distinguish schedules.

Daily gaps are calculated only between adjacent meetings on the same weekday.
Touching meetings have a zero-minute gap. Days without classes do not create
gaps. Gaps from 30 through 90 minutes receive a fragmented-gap penalty; gaps
over 90 minutes are reported as long-gap tradeoffs.

## Ranking

Schedules are sorted by:

1. Higher total score.
2. Fewer total gap minutes.
3. Later earliest weekly meeting.
4. Lexicographic course and section signature.

Ranks start at 1 and are stable for identical input. `topN` truncation happens
only after all legal candidates are scored and sorted.

## Reasons and Tradeoffs

Base reasons and tradeoffs are generated directly from selected sections and
the score breakdown. They never depend on AI. Fixed-section reasons, day-off
tradeoffs, early-start tradeoffs, and gap details therefore remain tied to real
schedule facts.

Optional AI rewriting receives only base explanations and an allowlisted
schedule summary. Its response must match a strict JSON schema and preserve the
number of explanation items. The backend rejects references to unknown course
codes, section IDs, weekdays, or times. Invalid JSON, provider failures, or
ungrounded text fall back to the deterministic explanations. Scores and ranks
are calculated before rewriting and cannot be changed by it.

## Empty and Failure Results

No legal candidates is a successful HTTP 200 response:

```json
{
  "interpretedPreferences": {},
  "schedules": [],
  "count": 0,
  "warnings": ["No legal schedules satisfy all hard constraints"]
}
```

The actual `interpretedPreferences` value includes all defaulted schema fields.
Preference-parser failures remain API errors and stop before scheduler
execution. Reason-rewriter failures do not fail generation and use fallback
text.

## Tests

```bash
cd backend
source .venv/bin/activate
pytest
```

The test suite uses mocked AI clients. It does not call a live AI API.
