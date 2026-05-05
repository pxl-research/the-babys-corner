from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import session, staff, admin

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
    await init_db()


app.include_router(session.router)
app.include_router(staff.router)
app.include_router(admin.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
