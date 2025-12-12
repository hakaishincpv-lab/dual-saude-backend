from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")

router = APIRouter(tags=["Web"])


@router.get("/painel")
def painel_home(request: Request):
    return templates.TemplateResponse(
        "painel_home.html",
        {"request": request, "title": "Painel Dual Saúde"},
    )
