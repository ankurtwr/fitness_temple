"""
FastAPI application — wires together all routers, templates, and static files.
"""

from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request
from starlette.responses import RedirectResponse, JSONResponse

from app.config import settings
from app.database import engine
from app.models import Base
from app.seed import run_seed

# ── Structured logging ──
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.PrintLoggerFactory(),
)
log = structlog.get_logger()

# ── Paths ──
BASE_DIR = Path(__file__).resolve().parent

# ── App ──
app = FastAPI(
    title="Fitness Temple — RFID Attendance System",
    version="0.1.0",
    docs_url="/docs",
    redoc_url=None,
)

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static files & templates ──
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


# ── Custom exception handler: redirect 303 to /login for page requests ──
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 303 and "Location" in (exc.headers or {}):
        return RedirectResponse(url=exc.headers["Location"], status_code=303)
    if exc.status_code == 401:
        accept = request.headers.get("accept", "")
        if "text/html" in accept:
            return RedirectResponse(url="/login", status_code=303)
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


# ── Register routers ──
from app.routers import scan, auth, dashboard, members, public  # noqa: E402

app.include_router(public.router)
app.include_router(scan.router)
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(members.router)


# ── Startup ──
@app.on_event("startup")
def on_startup():
    log.info("startup", action="creating_tables")
    Base.metadata.create_all(bind=engine)
    log.info("startup", action="seeding_data")
    run_seed()

    # Sync generated high-res fitness assets to static/img if present
    import shutil
    brain_dir = Path(r"C:\Users\Anuj\.gemini\antigravity-ide\brain\8bd5c50b-1175-4e97-aa88-78ec69ee7b60")
    img_dir = BASE_DIR / "static" / "img"
    img_dir.mkdir(parents=True, exist_ok=True)
    mappings = {
        "hero_athlete.jpg": "hero_bodybuilder_*.jpg",
        "program_strength.jpg": "program_strength_*.jpg",
        "program_muscle.jpg": "program_muscle_*.jpg",
        "program_trainer.jpg": "program_trainer_*.jpg",
    }
    for dest_name, pattern in mappings.items():
        matches = list(brain_dir.glob(pattern))
        if matches and not (img_dir / dest_name).exists():
            try:
                shutil.copy(matches[0], img_dir / dest_name)
            except Exception:
                pass

    log.info("startup", status="ready")


@app.get("/health")
def health_check():
    return {"status": "ok"}
