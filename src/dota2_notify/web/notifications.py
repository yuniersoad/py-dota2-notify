from dota2_notify.app.config import Settings, get_settings
from dota2_notify.clients.cosmosdb_client import CosmosDbUserService
from .dependencies import get_user_service, get_redis_client, template_obj
from fastapi import APIRouter, HTTPException, Request, Depends, WebSocket, WebSocketDisconnect, status as http_status
from .auth import get_current_user
from dota2_notify.models.user import steam_id_to_account_id
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional
import asyncio
import json
import logging

logger = logging.getLogger(__name__)

TELEGRAM_VERIFIED_CHANNEL = "telegram_verified:{account_id}"
WS_TIMEOUT_SECONDS = 600  # 10 minutes

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

@router.post("/reset")
async def reset_telegram_connection(steam_id: str = Depends(get_current_user), user_service: CosmosDbUserService = Depends(get_user_service)):
    if steam_id is None:
        return RedirectResponse(url="/", status_code=http_status.HTTP_303_SEE_OTHER)

    account_id = steam_id_to_account_id(int(steam_id))
    user = await user_service.get_user_async(account_id)

    if user:
        user.telegram_chat_id = ""
        new_token = await user_service.create_telegram_verify_token_async(account_id)
        user.telegram_verify_token = new_token
        await user_service.update_user_async(user)

    return RedirectResponse(url="/notifications", status_code=http_status.HTTP_303_SEE_OTHER)

@router.get("/")
async def get_notifications(request: Request,  steam_id: str = Depends(get_current_user), user_service: CosmosDbUserService = Depends(get_user_service)):
    if steam_id is None:
        return RedirectResponse(url="/", status_code=http_status.HTTP_303_SEE_OTHER)
    
    account_id = steam_id_to_account_id(int(steam_id))
    user = await user_service.get_user_async(account_id)
    
    steam_client = request.app.state.steam_client
    current_user_summary = None
    current_user_summary_list = await steam_client.get_player_summaries(steam_id, [steam_id])
    if current_user_summary_list:
        current_user_summary = current_user_summary_list[0]

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
            "current_user_summary": current_user_summary,
            "verified": verified,
            "token": user.telegram_verify_token,
            "flash_message": flash_message
        })

@router.get("/is_telegram_connected")
async def is_telegram_connected(request: Request, steam_id: str = Depends(get_current_user), user_service: CosmosDbUserService = Depends(get_user_service)):
    if steam_id is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    account_id = steam_id_to_account_id(int(steam_id))
    user = await user_service.get_user_async(account_id)

    return {"connected": user.is_telegram_verified}


@router.websocket("/ws")
async def telegram_verification_ws(websocket: WebSocket, steam_id: str = Depends(get_current_user), redis=Depends(get_redis_client)):
    if steam_id is None:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    account_id = steam_id_to_account_id(int(steam_id))
    channel = TELEGRAM_VERIFIED_CHANNEL.format(account_id=account_id)

    pubsub = redis.pubsub()
    await pubsub.subscribe(channel)
    logger.info(f"WebSocket opened for account_id={account_id}, subscribed to {channel}")

    try:
        deadline = asyncio.get_event_loop().time() + WS_TIMEOUT_SECONDS
        while True:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                await websocket.send_text(json.dumps({"connected": False, "reason": "timeout"}))
                break

            message = await asyncio.wait_for(pubsub.get_message(ignore_subscribe_messages=True), timeout=min(remaining, 1.0))
            if message is not None:
                await websocket.send_text(json.dumps({"connected": True}))
                break

    except asyncio.TimeoutError:
        pass
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for account_id={account_id}")
    except Exception as e:
        logger.error(f"WebSocket error for account_id={account_id}: {e}")
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
        logger.info(f"WebSocket closed for account_id={account_id}")
        try:
            await websocket.close()
        except Exception:
            pass


@router.post("/telegram-webhook/74ad1s_{secret}")
async def telegram_webhook(secret: str, update: TelegramUpdate, user_service: CosmosDbUserService = Depends(get_user_service), settings: Settings = Depends(get_settings), redis=Depends(get_redis_client)):
    
    if secret != settings.telegram_bot_token:
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
                    channel = TELEGRAM_VERIFIED_CHANNEL.format(account_id=account_id)
                    await redis.publish(channel, "connected")
                    logger.info(f"Published to {channel} after Telegram verification for account_id={account_id}")
    
    return {"status": "ok"}