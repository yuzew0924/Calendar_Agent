from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Calendar Agent API",
    description="Backend service for generating and ranking course schedules.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root() -> dict[str, str]:
    return {
        "service": "Calendar Agent API",
        "status": "ok",
    }


@app.get("/health")
def read_health() -> dict[str, str]:
    return {"status": "ok"}
