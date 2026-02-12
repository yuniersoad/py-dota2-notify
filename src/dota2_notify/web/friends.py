import asyncio
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request, Depends, status as http_status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from dota2_notify.models.user import Friend
from .auth import get_current_user

router = APIRouter()

top = Path(__file__).resolve().parent
template_obj = Jinja2Templates(directory=f"{top}/templates")

@router.get("/")
async def get_friends(request: Request,  steam_id: str = Depends(get_current_user)):
    user_service = request.app.state.user_service
    steam_client = request.app.state.steam_client
    
    user = None
    following = []
    not_following = []
    
    if steam_id is not None:
        account_id = user_service.steam_id_to_account_id(int(steam_id))
        
        user, friends_steam_ids, db_friends = await asyncio.gather(
            user_service.get_user_with_steam_id_async(int(steam_id)),
            steam_client.get_friend_list(steam_id),
            user_service.get_friends_async(account_id)
        )
        
        player_summaries = await steam_client.get_player_summaries(friends_steam_ids)
        
        # Map account_id -> following_status
        # db_friends.id is the account_id as string
        following_map = {f.id: f.following for f in db_friends}
        
        for summary in player_summaries:
            summary_account_id = str(user_service.steam_id_to_account_id(int(summary.steamid)))
            is_following = following_map.get(summary_account_id, False)
            
            if is_following:
                following.append(summary)
            else:
                not_following.append(summary)
    
    flash_message = getattr(request.state, "flash_message", None)

    return template_obj.TemplateResponse(
        request, 
        "friends.html", 
        { 
            "steam_id": steam_id, 
            "user": user, 
            "following": following,
            "not_following": not_following,
            "flash_message": flash_message
        }
    )

@router.post("/follow/{friend_steam_id}")
async def follow_friend(request: Request, friend_steam_id: int, steam_id: str = Depends(get_current_user)):
    user_service = request.app.state.user_service
    steam_client = request.app.state.steam_client

    if steam_id is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    

    friend = await user_service.get_friend_by_steam_id_async(int(steam_id), friend_steam_id)
    if friend is None:
        friend_list = await steam_client.get_friend_list(int(steam_id))
        friend_account_id = user_service.steam_id_to_account_id(friend_steam_id)

        if str(friend_steam_id) in friend_list: # it is a new friend that is not in the database yet, but is in the steam friend list
            friend_summary = await steam_client.get_player_summaries([str(friend_steam_id)])
            
            last_match_response, public_profile = await steam_client.get_match_history(str(friend_steam_id), matches_requested=1)

            if not public_profile:
                response = RedirectResponse(url="/", status_code=http_status.HTTP_303_SEE_OTHER)
                response.set_cookie(key="flash_message", value="Profile is private and cannot be followed.")
                return response

            friend = Friend(
                id=str(friend_account_id),
                user_id=user_service.steam_id_to_account_id(int(steam_id)),
                name=friend_summary[0].personaname if friend_summary else "Unknown",
                last_match_id=last_match_response["result"]["matches"][0]["match_id"], #TODO make the response parsing into a class with the proper types and names
                following=True
            )
        else: # not a friend at all
            return RedirectResponse(url="/", status_code=http_status.HTTP_303_SEE_OTHER)
                
    friend.following = True
    
    await user_service.update_friend_async(friend)
    return RedirectResponse(url="/", status_code=http_status.HTTP_303_SEE_OTHER)

@router.post("/unfollow/{friend_steam_id}")
async def unfollow_friend(request: Request, friend_steam_id: int, steam_id: str = Depends(get_current_user)):
    user_service = request.app.state.user_service

    if steam_id is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    friend = await user_service.get_friend_by_steam_id_async(int(steam_id), friend_steam_id)
    if friend is None:
        return RedirectResponse(url="/", status_code=http_status.HTTP_303_SEE_OTHER)
                
    friend.following = False
    
    await user_service.update_friend_async(friend)
    return RedirectResponse(url="/", status_code=http_status.HTTP_303_SEE_OTHER)
