import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_runtime_config_issues
from app.database import init_db
from app.routers import session, staff, admin

logger = logging.getLogger(__name__)

app = FastAPI(title="The Baby's Corner API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    for issue in get_runtime_config_issues():
        logger.warning("Runtime config issue: %s", issue)
    await init_db()


app.include_router(session.router)
app.include_router(staff.router)
app.include_router(admin.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
