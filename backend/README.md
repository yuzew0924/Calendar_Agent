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

The test suite verifies that `GET /health` returns HTTP `200` and the JSON
payload `{"status": "ok"}`.
