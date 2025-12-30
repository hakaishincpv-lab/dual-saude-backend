from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["Web"])


@router.get("/painel", response_class=HTMLResponse)
def painel_home(request: Request):
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "painel_home.html",
        {"request": request, "title": "Painel Dual Saúde"},
    )
