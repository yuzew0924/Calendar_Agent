# Backend

This directory will contain the Python backend for Calendar Agent.

Responsibilities:

- FastAPI application entry point.
- Schedule generation endpoints.
- Request and response models.
- Conflict detection.
- Gap analysis.
- Schedule scoring.
- Future OCR or AI-assisted course extraction.

The schemas are centralized in `app/models.py`. `ScheduleRequest` accepts the
documented camelCase JSON fields while exposing snake_case Python attributes.
Course components are defined only by each course's explicit `groups`; parsing
never adds an absent quiz, lab, or other component. `Preferences` is the
scheduler-facing model. AI output must validate as `ParsedPreferences` and be
converted with `to_scheduler_preferences()` before entering a
`ScheduleRequest`; raw AI text never enters the solver.

## AI Client

The `app/ai/` package is the only OpenAI integration boundary:

- `client.py` loads `OPENAI_API_KEY`, `OPENAI_MODEL`, and
  `AI_PREFERENCE_TIMEOUT_SECONDS`, creates the asynchronous Responses API
  client, and translates SDK failures into application errors.
- `context.py` creates an allowlisted course catalog containing only course
  code, title, section ID/type/status, and meeting days/start/end times.
- `prompts.py` owns model instructions and the strict JSON response schema.
- `preference_parser.py` validates model output through `ParsedPreferences`.

The preference parser sends the user's text together with context built from
the request's validated `courses`. It never sends SLNs, locations, dependency
IDs, group configuration, or other unnecessary fields. The prompt forbids
references outside that catalog. After schema validation, the parser builds a
`ScheduleRequest` with the original courses, so nonexistent sections and closed
fixed sections under open-only mode are rejected before reaching the solver.
The client sends the schema through the Responses API `text.format` structured
output configuration. The schema requires every known field and rejects extra
properties. Pydantic then performs a separate validation pass for `HH:MM`
times, weekday codes, strict field types, fixed-section syntax, and consistent
conflict or clarification metadata.

`build_section_index()` creates the grounding index used by
`validate_and_convert_preferences()`. Conversion rejects unknown course codes,
section IDs that do not belong to the referenced course, and closed fixed
sections when open-only mode is active. Only then does it return the scheduler's
`dict[str, list[str]]` fixed-section representation.

The prompt treats approximate wording such as "not too early," "prefer Friday
off," and "try to avoid long gaps" as soft. It leaves an unspecified start time
as `null`. Explicit mandatory wording with an exact value may become a hard
constraint; unresolved mandatory wording produces clarification metadata
instead of an invented filter.

Call `get_ai_client()` to reuse the process-wide configured client. Missing or
invalid configuration raises `AIConfigurationError`. Timeouts, connection
failures, authentication failures, rate limits, provider HTTP failures, and
empty responses use distinct error codes. Malformed JSON, Markdown-wrapped
JSON, and schema-invalid output are rejected by the parser. No failure path
creates fallback preferences or invokes schedule generation.
FastAPI serializes every `AIClientError` as:

```json
{
  "error": {
    "code": "ai_request_timeout",
    "message": "AI request timed out after 20 seconds"
  }
}
```

Stable AI error codes include `ai_request_timeout`, `ai_authentication_failed`,
`ai_rate_limited`, `ai_connection_failed`, `ai_provider_error`,
`ai_invalid_response`, and `ai_preference_conflict`. Preference conflicts use
HTTP 409; provider failures use 502, rate limits and missing configuration use
503, and timeouts use 504.

After grounding, the backend detects contradictions between fixed sections and
hard earliest-start or required-day-off constraints. It also rejects multiple
fixed alternatives from one section group. AI-reported conflicts remain
blocking even if the backend cannot infer the same contradiction independently.

No AI client is created during application import, so health endpoints and
non-AI features continue to work without an API key.

## Preference Parsing Endpoint

`POST /parse-preferences` accepts a validated course catalog and non-empty
`preferenceText`. It sends only the allowlisted AI context, validates the strict
JSON response as `ParsedPreferences`, grounds fixed-section references, and
checks deterministic hard conflicts. Its response model is `ParsedPreferences`;
raw provider output is never serialized to the caller.

The endpoint intentionally does not invoke the scheduler. A successful caller
may use `validate_and_convert_preferences()` to obtain `Preferences` for the
Week 3 engine. Conversion preserves `requireOpenSections`, fixed sections,
earliest-start semantics, `requiredDaysOff`, and `preferredDaysOff`. The solver
uses only hard fields for filtering; `preferredDaysOff` and other soft metadata
remain available for Week 5 scoring.

Tests use injected fake AI clients and never call the real API:

```bash
pytest tests/ai
```

Weekday and time normalization is centralized in `app/scheduler/time_utils.py`.
Scheduling algorithms compare `Weekday` values and integer minutes since
midnight rather than raw input strings. `app/normalization.py` remains as a
compatibility import path.

The framework-independent scheduler is split by responsibility:

- `app/scheduler/time_utils.py`: weekday normalization, time parsing, and
  meeting overlap checks.
- `app/scheduler/solver.py`: one-section-per-group combinations, open/fixed
  filtering, dependency checks, and conflict-free multi-course combinations.
- `app/scheduler/scoring.py`: schedule scoring extension point.
- `app/scheduler/explanations.py`: human-readable explanation extension point.

FastAPI routes should validate requests and serialize responses; scheduling
rules belong in these modules so tests and other callers can use them directly.

The solver preserves two explicit Cartesian-product levels. A
`CourseCombination` contains one `SectionChoice` for every declared group in
one course. A `ScheduleCandidate` contains one `CourseCombination` for every
course in request order. Group, section, and course input order is preserved,
so repeated calls with the same request return candidates in the same order.

Hard constraints are applied to every candidate. Meeting conflicts use
half-open intervals: two meetings conflict only when they share a weekday and
`a.start < b.end and b.start < a.end`. Fixed sections must survive open-only
filtering and must still pass intra-course and cross-course conflict checks.
The solver pipeline is:

1. Filter ineligible sections when open-only is enabled.
2. Generate one choice per declared group.
3. Build course-level Cartesian products.
4. Apply fixed-section and course-level hard constraints.
5. Build the multi-course Cartesian product.
6. Apply the unified schedule hard-constraint gate, including conflicts.
7. Return only valid schedules, or an empty tuple when none exist.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

The API exposes:

- `GET /`
- `GET /health`

## Test

With the backend virtual environment activated, run:

```bash
pytest
```

The test suite covers the health endpoint, schemas, normalization, meeting
overlap checks, and the framework-independent solver. It also validates
`sample-data/courses.json` through `GenerateScheduleRequest`, runs the complete
scheduler pipeline, and verifies conflict-free deterministic output.
