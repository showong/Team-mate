"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.api.routes_health import router as health_router
from app.api.routes_projects import router as projects_router
from app.api.routes_reports import router as reports_router

app = FastAPI(
    title="Team-mate",
    description="Multi-LLM virtual department for AI-assisted research (Phase 1).",
    version="0.1.0",
)

app.include_router(health_router)
app.include_router(projects_router)
app.include_router(reports_router)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")
