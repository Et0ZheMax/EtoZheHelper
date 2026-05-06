from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.api.chat import router as api_router
from app.audit.logger import log_event
from app.config import get_settings
from app.db import SessionLocal, init_db
from app.web.routes import router as web_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    db: Session = SessionLocal()
    try:
        log_event(db, "app_started", {"app": get_settings().app_name, "env": get_settings().app_env})
    finally:
        db.close()
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(api_router, prefix="/api")
app.include_router(web_router)
