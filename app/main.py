from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
import os
import logging

from app.config import get_settings
from app.database import init_db, get_db, async_session
from app.routers import auth, github, recommendations
from app.models import User
from app.tasks.scheduler import start_scheduler, stop_scheduler
from sqlalchemy import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting StarDiscover...")
    await init_db()
    start_scheduler()
    logger.info("StarDiscover started successfully")
    yield
    # Shutdown
    logger.info("Shutting down StarDiscover...")
    stop_scheduler()


app = FastAPI(
    title="StarDiscover",
    description="GitHub Stars Recommendation Engine",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

# Static files and templates
templates_path = os.path.join(os.path.dirname(__file__), "templates")
static_path = os.path.join(os.path.dirname(__file__), "static")

if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")

templates = Jinja2Templates(directory=templates_path)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(github.router, prefix="/api/github", tags=["github"])
app.include_router(recommendations.router, prefix="/api/recommendations", tags=["recommendations"])


async def get_current_user(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    async with async_session() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = await get_current_user(request)
    if not user:
        return templates.TemplateResponse("login.html", {"request": request})
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user})


@app.get("/recommendations", response_class=HTMLResponse)
async def recommendations_page(request: Request):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse(url="/auth/login")
    return templates.TemplateResponse("recommendations.html", {"request": request, "user": user})


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "stardiscover"}
