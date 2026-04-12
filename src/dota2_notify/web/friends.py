import asyncio
from fastapi import APIRouter, HTTPException, Request, Depends, status as http_status
from fastapi.responses import RedirectResponse

from dota2_notify.clients.cosmosdb_client import CosmosDbUserService
from dota2_notify.clients.steam_client import SteamClient
from dota2_notify.models.user import Friend, steam_id_to_account_id
from .auth import get_current_user
from .dependencies import get_steam_client, get_user_service, template_obj

router = APIRouter()


@router.get("/")
async def get_friends(
    request: Request,  
    steam_id: str = Depends(get_current_user), 
    user_service: CosmosDbUserService = Depends(get_user_service),
    steam_client: SteamClient = Depends(get_steam_client)):
    
    user = None
    current_user_summary = None
    following = []
    not_following = []
    
    if steam_id is not None:
        account_id = steam_id_to_account_id(int(steam_id))
        
        user, friends_steam_ids, db_friends, current_user_summary_list = await asyncio.gather(
            user_service.get_user_with_steam_id_async(int(steam_id)),
            steam_client.get_friend_list(steam_id),
            user_service.get_friends_async(account_id),
            steam_client.get_player_summaries(steam_id,[steam_id])
        )
        
        if current_user_summary_list:
            current_user_summary = current_user_summary_list[0]
        
        player_summaries = await steam_client.get_player_summaries(steam_id, friends_steam_ids, cache=True) # Only cache friend list summaries, not the current user summary since it is needed for the friends page and may change frequently with the profile updates and the following/unfollowing actions
        
        # Map account_id -> following_status
        # db_friends.id is the account_id as string
        following_map = {f.id: f.following for f in db_friends}
        
        for summary in player_summaries:
            summary_account_id = str(steam_id_to_account_id(int(summary.steamid)))
            is_following = following_map.get(summary_account_id, False)
            
            if is_following:
                following.append(summary)
            else:
                not_following.append(summary)

        # Include the current user in the list so they can follow/unfollow themselves
        if user is not None and current_user_summary is not None:
            if user.following:
                following.append(current_user_summary)
            else:
                not_following.append(current_user_summary)
    
    following.sort(key=lambda x: x.personaname)
    not_following.sort(key=lambda x: x.personaname)

    flash_message = getattr(request.state, "flash_message", None)

    return template_obj.TemplateResponse(
        request, 
        "friends.html", 
        { 
            "steam_id": steam_id, 
            "user": user, 
            "current_user_summary": current_user_summary,
            "following": following,
            "not_following": not_following,
            "flash_message": flash_message
        }
    )

@router.post("/follow/{friend_steam_id}")
async def follow_friend(
    friend_steam_id: int, 
    steam_id: str = Depends(get_current_user), 
    user_service: CosmosDbUserService = Depends(get_user_service), 
    steam_client: SteamClient = Depends(get_steam_client)):
    
    if steam_id is None:
        return RedirectResponse(url="/", status_code=http_status.HTTP_303_SEE_OTHER)

    if friend_steam_id == int(steam_id):
        user = await user_service.get_user_with_steam_id_async(int(steam_id))
        if user is not None:
            user.following = True
            await user_service.update_user_async(user)
        return RedirectResponse(url="/", status_code=http_status.HTTP_303_SEE_OTHER)

    friend_summary = await steam_client.get_player_summaries(steam_id, [str(friend_steam_id)])
    _, public_profile = await steam_client.get_match_history(str(friend_steam_id), matches_requested=1)

    if not public_profile:
        response = RedirectResponse(url="/", status_code=http_status.HTTP_303_SEE_OTHER)
        response.set_cookie(key="flash_message", value="Profile is private and cannot be followed.")
        return response
    
    friend = await user_service.get_friend_by_steam_id_async(int(steam_id), friend_steam_id)
    if friend is None:
        friend_list = await steam_client.get_friend_list(int(steam_id))
        friend_account_id = steam_id_to_account_id(friend_steam_id)

        if str(friend_steam_id) in friend_list: # it is a new friend that is not in the database yet, but is in the steam friend list
            friend = Friend(
                id=str(friend_account_id),
                user_id=steam_id_to_account_id(int(steam_id)),
                name=friend_summary[0].personaname if friend_summary else "Unknown",
                following=True
            )
        else: # not a friend at all
            return RedirectResponse(url="/", status_code=http_status.HTTP_303_SEE_OTHER)
                
    friend.following = True
    friend.name = friend_summary[0].personaname if friend_summary else friend.name # Update the name in case it changed on Steam
    
    await user_service.update_friend_async(friend)
    return RedirectResponse(url="/", status_code=http_status.HTTP_303_SEE_OTHER)

@router.post("/unfollow/{friend_steam_id}")
async def unfollow_friend(
    friend_steam_id: int, 
    steam_id: str = Depends(get_current_user), 
    user_service: CosmosDbUserService = Depends(get_user_service)):
    
    if steam_id is None:
        return RedirectResponse(url="/", status_code=http_status.HTTP_303_SEE_OTHER)

    if friend_steam_id == int(steam_id):
        user = await user_service.get_user_with_steam_id_async(int(steam_id))
        if user is not None:
            user.following = False
            await user_service.update_user_async(user)
        return RedirectResponse(url="/", status_code=http_status.HTTP_303_SEE_OTHER)

    friend = await user_service.get_friend_by_steam_id_async(int(steam_id), friend_steam_id)
    if friend is None:
        return RedirectResponse(url="/", status_code=http_status.HTTP_303_SEE_OTHER)
                
    friend.following = False
    
    await user_service.update_friend_async(friend)
    return RedirectResponse(url="/", status_code=http_status.HTTP_303_SEE_OTHER)
