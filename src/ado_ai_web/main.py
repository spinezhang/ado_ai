"""FastAPI application entry point for ADO AI Web Service."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

# Import API routers
from ado_ai_web.api import setup, config, work_items, files

# Create FastAPI app
app = FastAPI(
    title="ADO AI Web Service",
    description="Azure DevOps AI Auto-Complete Tool - Web Interface",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup paths
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Register API routers
app.include_router(setup.router)
app.include_router(config.router)
app.include_router(work_items.router)
app.include_router(files.router)


# Root route
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root endpoint - redirects to setup or dashboard."""
    from ado_ai_web.database.session import get_db
    from ado_ai_web.services.settings_manager import SettingsManager

    # Check if user is configured
    db = next(get_db())
    try:
        manager = SettingsManager(db)
        user = manager.get_default_user()

        if user:
            return RedirectResponse(url="/dashboard")
        else:
            return RedirectResponse(url="/setup")
    finally:
        db.close()


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "service": "ado-ai-web"}


# Setup route (temporary placeholder)
@app.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request):
    """First-run setup page."""
    return templates.TemplateResponse(
        "setup.html",
        {"request": request, "title": "Setup - ADO AI"}
    )


# Dashboard route (temporary placeholder)
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Main dashboard page."""
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "title": "Dashboard - ADO AI"}
    )


# Work item detail page
@app.get("/work-items/new", response_class=HTMLResponse)
async def work_item_page(request: Request):
    """Work item analysis page."""
    return templates.TemplateResponse(
        "work_item_detail.html",
        {"request": request, "title": "Analyze Work Item - ADO AI"}
    )


# Work item history detail page
@app.get("/work-items/history/{history_id}", response_class=HTMLResponse)
async def work_item_history_page(request: Request, history_id: int):
    """View saved work item analysis."""
    return templates.TemplateResponse(
        "work_item_history.html",
        {"request": request, "title": "Analysis Result - ADO AI"}
    )


# Settings page
@app.get("/settings", response_class=HTMLResponse)
@app.get("/config", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Settings configuration page."""
    return templates.TemplateResponse(
        "settings.html",
        {"request": request, "title": "Settings - ADO AI"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "ado_ai_web.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
