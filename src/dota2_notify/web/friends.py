from pathlib import Path
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.templating import Jinja2Templates
from .auth import get_current_user

router = APIRouter()

top = Path(__file__).resolve().parent
template_obj = Jinja2Templates(directory=f"{top}/templates")

@router.get("/")
async def get_friends(request: Request,  steam_id: str = Depends(get_current_user)):
    return template_obj.TemplateResponse("friends.html", {"request": request, "steam_id": steam_id, "friends": ["Friend1", "Friend2", "Friend3"]})