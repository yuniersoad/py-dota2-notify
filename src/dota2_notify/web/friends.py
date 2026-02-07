import asyncio
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.templating import Jinja2Templates
from .auth import get_current_user

router = APIRouter()

top = Path(__file__).resolve().parent
template_obj = Jinja2Templates(directory=f"{top}/templates")

@router.get("/")
async def get_friends(request: Request,  steam_id: str = Depends(get_current_user)):
    user = None
    friends = []
    player_summaries = []
    if steam_id is not None:
        user, friends = await asyncio.gather(
            request.app.state.user_service.get_user_with_steam_id_async(int(steam_id)),
            request.app.state.steam_client.get_friend_list(steam_id)
        )
        player_summaries = await request.app.state.steam_client.get_player_summaries(
            [friend["steamid"] for friend in friends.get("friendslist", {}).get("friends", [])]
        )
    return template_obj.TemplateResponse(request, "friends.html", { "steam_id": steam_id, "user": user, "friends": player_summaries})