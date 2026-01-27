from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()

top = Path(__file__).resolve().parent
template_obj = Jinja2Templates(directory=f"{top}/templates")

@router.get("/")
async def get_friends(request: Request):
    return template_obj.TemplateResponse("friends.html", {"request": request, "friends": ["Friend1", "Friend2", "Friend3"]})