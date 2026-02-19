from .dependencies import template_obj
from fastapi import APIRouter, HTTPException, Request, Depends
from .auth import get_current_user
from dota2_notify.models.user import steam_id_to_account_id
from fastapi.responses import RedirectResponse

router = APIRouter(prefix="/notifications")

@router.post("/reset")
async def reset_telegram_connection(request: Request, steam_id: str = Depends(get_current_user)):
    if steam_id is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    user_service = request.app.state.user_service
    account_id = steam_id_to_account_id(int(steam_id))
    user = await user_service.get_user_async(account_id)

    if user:
        user.telegram_chat_id = ""
        new_token = await user_service.create_telegram_verify_token_async(account_id)
        user.telegram_verify_token = new_token
        await user_service.update_user_async(user)

    return RedirectResponse(url="/notifications", status_code=303)

@router.get("/")
async def get_notifications(request: Request,  steam_id: str = Depends(get_current_user)):
    user_service = request.app.state.user_service
    
    if steam_id is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    account_id = steam_id_to_account_id(int(steam_id))
    user = await user_service.get_user_async(account_id)

    verified = bool(user.telegram_chat_id.strip())
    if not verified:
        token = user.telegram_verify_token
        if not bool(token.strip()) or not (await user_service.get_user_id_by_telegram_token_async(token) == account_id):
            token = await user_service.create_telegram_verify_token_async(account_id)
            user.telegram_verify_token = token
            await user_service.update_user_async(user)
    
    flash_message = getattr(request.state, "flash_message", None)

    return template_obj.TemplateResponse(
        request, 
        "notifications.html", 
        { 
            "steam_id": steam_id, 
            "user": user,
            "verified": verified,
            "token": user.telegram_verify_token,
            "flash_message": flash_message
        })