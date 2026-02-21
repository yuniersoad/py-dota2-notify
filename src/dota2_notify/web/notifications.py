import os
from .dependencies import template_obj
from fastapi import APIRouter, HTTPException, Request, Depends
from .auth import get_current_user
from dota2_notify.models.user import steam_id_to_account_id
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional

class TelegramUser(BaseModel):
    id: int
    is_bot: bool
    first_name: str
    username: Optional[str] = None

class TelegramChat(BaseModel):
    id: int
    type: str
    first_name: Optional[str] = None
    username: Optional[str] = None

class TelegramMessage(BaseModel):
    message_id: int
    from_user: Optional[TelegramUser] = None
    chat: TelegramChat
    date: int
    text: Optional[str] = None

class TelegramUpdate(BaseModel):
    update_id: int
    message: Optional[TelegramMessage] = None

router = APIRouter(prefix="/notifications")
telegram_bot_token = os.getenv("TELEGRAM__BOTTOKEN") # TODO: use pydantic settings

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

    verified = user.is_telegram_verified
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

@router.get("/is_telegram_connected")
async def is_telegram_connected(request: Request, steam_id: str = Depends(get_current_user)):
    user_service = request.app.state.user_service
    
    if steam_id is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    account_id = steam_id_to_account_id(int(steam_id))
    user = await user_service.get_user_async(account_id)

    return {"connected": user.is_telegram_verified}


@router.post("/telegram-webhook/74ad1s_{secret}")
async def telegram_webhook(secret: str, update: TelegramUpdate, request: Request):
    user_service = request.app.state.user_service
    
    if secret != telegram_bot_token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if update.message and update.message.text and update.message.text.startswith("/start"):
        parts = update.message.text.split()
        if len(parts) == 2:
            token = parts[1]
            account_id = await user_service.get_user_id_by_telegram_token_async(token)
            if account_id:
                user = await user_service.get_user_async(account_id)
                if user:
                    user.telegram_chat_id = str(update.message.chat.id)
                    user.telegram_username = update.message.chat.username or ""
                    user.telegram_verify_token = ""
                    await user_service.update_user_async(user)
                    await user_service.delete_telegram_verify_token_async(token)
    
    return {"status": "ok"}