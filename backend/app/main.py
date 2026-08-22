from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    admin,
    auth,
    clients,
    drafts,
    imports,
    metrics,
    scorecards,
    sessions,
    users,
    webhooks,
)
from app.jobs.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="CoachFlow API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to the deployed frontend origin before production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(clients.router, prefix="/api/clients", tags=["clients"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(drafts.router, prefix="/api/drafts", tags=["drafts"])
app.include_router(scorecards.router, prefix="/api/scorecards", tags=["scorecards"])
app.include_router(metrics.router, prefix="/api/metrics", tags=["metrics"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(imports.router, prefix="/api/admin/imports", tags=["admin", "imports"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
