from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates

from app.config import Settings, get_settings
from app.kb.loader import load_knowledge_base

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def index(request: Request, settings: Settings = Depends(get_settings)):
    documents = load_knowledge_base(settings.knowledge_base_dir)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "documents_count": len(documents),
            "knowledge_base_dir": str(settings.knowledge_base_dir),
        },
    )
