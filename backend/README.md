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
never adds an absent quiz, lab, or other component. `ParsedPreferences` is the
internal normalized preference model.

Weekday and time normalization is centralized in `app/scheduler/time_utils.py`.
Scheduling algorithms compare `Weekday` values and integer minutes since
midnight rather than raw input strings. `app/normalization.py` remains as a
compatibility import path.

The framework-independent scheduler is split by responsibility:

- `app/scheduler/time_utils.py`: weekday normalization, time parsing, and
  meeting overlap checks.
- `app/scheduler/solver.py`: exact section-group combinations, open/fixed
  filtering, dependency checks, and conflict-free multi-course combinations.
- `app/scheduler/scoring.py`: schedule scoring extension point.
- `app/scheduler/explanations.py`: human-readable explanation extension point.

FastAPI routes should validate requests and serialize responses; scheduling
rules belong in these modules so tests and other callers can use them directly.

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
overlap checks, and the framework-independent solver.
