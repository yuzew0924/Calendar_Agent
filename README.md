# Calendar Agent

Calendar Agent is a course schedule planning assistant that helps students compare possible class schedules before registration. Users can enter courses, available lecture and quiz sections, fixed choices, and scheduling preferences. The app then generates ranked schedule options and displays each one as a weekly calendar.

## Description

Planning a course schedule is often messy because every course may have several lectures, quiz sections, labs, availability states, and registration constraints. Calendar Agent is designed to turn that information into clear options.

The project focuses on three core problems:

- Finding conflict-free combinations across multiple courses.
- Ranking schedules based on personal preferences.
- Showing each result visually so the user can quickly judge whether the schedule feels too tight, too spread out, or acceptable.

The planned architecture uses a React frontend for the interactive calendar interface and a Python backend for schedule generation, scoring, and future AI-assisted input parsing.

## Features

- Enter courses with lectures, quiz sections, labs, and meeting times.
- Mark sections as fixed when the user has already chosen them.
- Filter by availability, such as open-only sections.
- Detect time conflicts across weekdays.
- Apply preferences such as avoiding early classes or avoiding awkward gaps.
- Generate multiple ranked schedule plans.
- Explain why each schedule is recommended or penalized.
- Visualize each schedule as a weekly calendar.
- Compare alternate course sets, such as `208 + 414 + 370 + 332` versus `351 + 414 + 370 + 332`.

## Tech Stack

- Frontend: React, TypeScript, Vite
- Backend: Python, FastAPI
- Scheduling Engine: Python service layer
- Testing: pytest for backend tests, Vitest for frontend tests
- Future AI Layer: OCR or LLM-assisted parsing for screenshots and pasted registration data

## Requirements

Planned development requirements:

- Node.js 20+
- Python 3.11+
- npm or pnpm
- pip
- Git

No external API key is required for the initial manual-input MVP. Future screenshot parsing or AI extraction features may require an API key.

## Installation

Clone the repository:

```bash
git clone <repository-url>
cd calendar-agent
```

Install frontend dependencies:

```bash
cd frontend
npm install
```

Install backend dependencies:

```bash
cd ../backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The backend uses FastAPI and Uvicorn.

## Usage

Start the backend:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

The backend runs at `http://127.0.0.1:8000` by default.

Start the frontend:

```bash
cd frontend
npm run dev
```

Open the local app:

```text
http://localhost:5173
```

Example workflow:

1. Add courses such as `MATH 208`, `CSE 414`, `INFO 370`, and `CSE 332`.
2. Enter each available lecture and quiz section.
3. Lock fixed sections, such as `CSE 414 C` and `CSE 414 CD`.
4. Set preferences, such as no classes before `9:30 AM` unless unavoidable.
5. Generate schedule options.
6. Compare the ranked results in the weekly calendar view.

## Example Input

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

This payload maps directly to `GenerateScheduleRequest`. The canonical field
definitions, defaults, validation rules, object relationships, and response
example are documented in [`docs/input-format.md`](docs/input-format.md).

## Project Structure

Current structure:

```text
calendar-agent/
├── README.md
├── .env.example
├── docs/
│   ├── agent-design.md
│   └── input-format.md
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── src/
│   │   ├── test/
│   │   │   └── setup.ts
│   │   ├── App.test.tsx
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── styles.css
│   │   └── vite-env.d.ts
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   └── vite.config.ts
├── backend/
│   ├── README.md
│   ├── pytest.ini
│   ├── requirements.txt
│   ├── app/
│   │   ├── __init__.py
│   │   └── main.py
│   └── tests/
│       └── test_health.py
└── sample-data/
    └── courses.json
```

Directory responsibilities:

- `frontend/`: React, TypeScript, and Vite application for course input, preference controls, schedule results, and calendar visualization.
- `backend/`: Python backend for schedule generation, scoring, API routes, and future AI-assisted extraction.
- `sample-data/`: Example course and preference payloads used for development and testing.
- `docs/`: Product notes, agent design, and input-format documentation.
- `.env.example`: Template for local configuration values.

## Configuration

Create a local environment file from the provided example:

```bash
cp .env.example .env
```

The example contains:

```bash
VITE_API_BASE_URL=http://localhost:8000
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
```

`VITE_API_BASE_URL` tells the React app where to reach FastAPI. Vite is configured
to load `.env` from the repository root. `BACKEND_HOST` and `BACKEND_PORT` define
the intended local backend bind address. Keep secrets in `.env`; Git ignores that
file, while `.env.example` documents safe placeholder values.

To run Uvicorn with the configured backend values:

```bash
cd backend
source .venv/bin/activate
set -a
source ../.env
set +a
uvicorn app.main:app --reload --host "$BACKEND_HOST" --port "$BACKEND_PORT"
```

## Testing

Run backend tests:

```bash
cd backend
pytest
```

Run frontend tests:

```bash
cd frontend
npm run test
```

Run the frontend tests continuously while editing:

```bash
cd frontend
npm run test:watch
```

The current frontend verification commands are:

```bash
cd frontend
npm run build
npm run dev
```

Testing should cover:

- Time parsing.
- Conflict detection.
- Gap calculation.
- Fixed-section handling.
- Schedule ranking.
- API request and response validation.
- Calendar rendering behavior.

## Known Issues / Limitations

- The app is currently in the planning/scaffold stage.
- Course data must initially be entered manually.
- Screenshot parsing is planned but not implemented yet.
- Seat availability refresh is planned but not implemented yet.
- The first version will focus on weekday schedules.

## Roadmap

- Build the Python scheduling engine.
- Add FastAPI endpoints for schedule generation.
- Build the React course input and preference UI.
- Add weekly calendar visualization.
- Add sample course data.
- Add import support for pasted registration tables.
- Add screenshot/OCR-assisted extraction.
- Add export to `.ics` calendar files.
- Add saved schedule scenarios.

## Contributing

This is currently a personal planning and portfolio project. A future contribution workflow may use:

1. Fork the repository.
2. Create a feature branch.
3. Make changes.
4. Run backend and frontend tests.
5. Open a pull request with a clear description.

## Author

Yz Wang

## License

License to be decided.
