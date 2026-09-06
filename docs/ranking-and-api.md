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
    "gapPreference": "none",
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
          "scoreDelta": 0,
          "matchedPreference": "11:00",
          "details": "All class days start at or after 11:00",
          "reasonCandidate": "All class days start at or after 11:00",
          "tradeoffCandidate": null,
          "affectedSections": ["CSE 373 A"],
          "affectedMeetings": [
            {
              "courseCode": "CSE 373",
              "sectionId": "A",
              "day": "M",
              "startTime": "11:30",
              "endTime": "12:20"
            }
          ]
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

Every rule preserves the complete scoring trace:

- `score` and `maximum` are the rule contribution and available points.
- `scoreDelta` is exactly `score - maximum`, making penalties explicit.
- `matchedPreference` identifies the user preference applied, or is `null` for
  a neutral default rule.
- `details` records the objective calculation.
- `reasonCandidate` and `tradeoffCandidate` are deterministic explanation
  inputs and may be `null`.
- `affectedSections` and `affectedMeetings` identify the real schedule data used
  by the rule.

The schedule's total `score` must equal the sum of every breakdown `score`; the
response model rejects inconsistent arithmetic.

## Deterministic Scoring

Scores range from 0 to 100 and do not use AI:

| Rule | Maximum | Behavior |
|---|---:|---|
| `earliestStart` | 25 | Penalizes each class day's first meeting before the preferred time; the penalty is halved when earlier classes are allowed as fallback |
| `preferredTimeOfDay` | 20 | Awards points by the proportion of weekly meetings in morning, afternoon, or evening |
| `gaps` | 30 | Applies compact, balanced, or breaks scoring only when the user expresses that preference; `none` is neutral |
| `preferredDaysOff` | 25 | Awards points by the proportion of preferred days that remain free |

Time-of-day buckets use meeting start time:

- Morning: before 12:00.
- Afternoon: 12:00 through 16:59.
- Evening: 17:00 or later.
- None: neutral and does not distinguish schedules.

Daily gaps are objective data calculated only between adjacent meetings on the
same weekday. Each gap records its weekday, start, end, minutes, and surrounding
meetings. Touching meetings have a zero-minute gap; different days and days
without classes do not create gaps.

`gapPreference` controls interpretation. `compact` rewards short or consecutive
gaps, `breaks` rewards useful rest periods, and `balanced` favors moderate gaps
without either extreme. With `none`, every schedule receives the same neutral
gap contribution and no compactness reason or gap trade-off is generated.

## Ranking

Schedules are sorted by:

1. Higher total score.
2. Fewer unsatisfied soft preferences.
3. Later earliest weekly meeting, only when an earliest-start preference exists.
4. Better preferred-days-off match, only when that preference exists.
5. Lexicographic course and section signature.

Gap minutes are not used as an implicit tie-breaker. They affect ranking only
through an explicit `gapPreference` score.

Ranks start at 1 and are stable for identical input. `topN` truncation happens
only after all legal candidates are scored and sorted.

## Reasons and Tradeoffs

Base reasons and tradeoffs are generated from selected fixed sections and the
`reasonCandidate` and `tradeoffCandidate` fields in the score breakdown. They
never depend on AI. A preference-neutral rule does not emit either candidate,
so defaults cannot produce preference claims.

Optional AI rewriting receives only base explanations and an allowlisted
schedule summary. Its response must match a strict JSON schema and preserve the
number of explanation items. The backend rejects references to unknown course
codes, section IDs, weekdays, times, or locations. Invalid JSON, provider failures, or
ungrounded text fall back to the deterministic explanations. Scores and ranks
are calculated before rewriting and cannot be changed by it.

## Empty and Failure Results

No legal candidates is a successful HTTP 200 response:

```json
{
  "interpretedPreferences": {},
  "schedules": [],
  "count": 0,
  "warnings": [
    "CSE 373 quiz group has no open sections while open-only is enabled."
  ]
}
```

The actual `interpretedPreferences` value includes all defaulted schema fields.
Warnings identify empty declared groups, open-only section exhaustion,
overlapping fixed sections, hard day/time filters, or conflicts among all
remaining combinations. Multiple applicable diagnostics are returned together.
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
