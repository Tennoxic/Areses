import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import (
    admin,
    articles,
    auth,
    events,
    extras,
    feeds,
    folders,
    saved_searches,
)
from app.core.config import settings
from app.db.session import reset_fetching_locks
from app.services import scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    await reset_fetching_locks()
    scheduler_task = asyncio.create_task(scheduler.run_forever())
    yield
    scheduler.stop()
    scheduler_task.cancel()
    try:
        await scheduler_task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="ARESES", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(feeds.router)
app.include_router(folders.router)
app.include_router(articles.router)
app.include_router(saved_searches.router)
app.include_router(admin.router)
app.include_router(events.router)
app.include_router(extras.router)


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "img-src 'self' https: data:; "
        "media-src 'self' https:; "
        "frame-src https://www.youtube.com https://www.youtube-nocookie.com https://player.vimeo.com; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "frame-ancestors 'self'"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    if not settings.local_mode:
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains"
        )
    return response

_dist_dir = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _dist_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(_dist_dir), html=True), name="frontend")
