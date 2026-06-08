import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_runtime_config_issues, get_startup_config_errors, settings
from app.database import init_db
from app.routers import session, staff, admin, filters, auth

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    errors = get_startup_config_errors()
    if errors:
        raise RuntimeError("Invalid production config: " + "; ".join(errors))
    for issue in get_runtime_config_issues():
        logger.warning("Runtime config issue: %s", issue)
    await init_db()
    yield


app = FastAPI(title="The Baby's Corner API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(session.router)
app.include_router(staff.router)
app.include_router(admin.router)
app.include_router(filters.router)
app.include_router(auth.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
