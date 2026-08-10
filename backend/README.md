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
