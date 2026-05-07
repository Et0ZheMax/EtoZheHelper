from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates

from app.config import TEMPLATES_DIR, Settings, get_settings
from app.kb.service import knowledge_base_service

router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@router.get("/")
def index(request: Request, settings: Settings = Depends(get_settings)):
    snapshot = knowledge_base_service.get_knowledge_base(settings.knowledge_base_dir)
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "app_name": settings.app_name,
            "documents_count": snapshot.stats.documents_count,
            "knowledge_base_dir": snapshot.stats.knowledge_base_dir,
            "domains": snapshot.stats.domains,
            "types": snapshot.stats.types,
            "risks": snapshot.stats.risks,
            "tags": snapshot.stats.tags,
        },
    )
