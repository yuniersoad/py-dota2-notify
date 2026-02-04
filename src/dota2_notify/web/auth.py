import os
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from urllib.parse import urlencode
import httpx
import re
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError

steam_openid_url = "https://steamcommunity.com/openid/login"
load_dotenv()
jwt_secret_key = os.getenv("JWT__COOKIES__SECRET") # TODO: use pydantic settings
cookie_name = "access_token"

router = APIRouter(prefix="/auth")

@router.get("/login")
async def login(request: Request):
    base_url = str(request.base_url).rstrip('/')
    params = {
        "openid.ns": "http://specs.openid.net/auth/2.0",
        "openid.mode": "checkid_setup",
        "openid.return_to": f"{base_url}/auth/steam/callback",
        "openid.realm": f"{base_url}/",
        "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
        "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select"
    }
    
    query_string = urlencode(params)
    redirect_url = f"{steam_openid_url}?{query_string}"
    
    return RedirectResponse(url=redirect_url)

@router.get("/steam/callback")
async def steam_callback(request: Request):
    params = dict(request.query_params)
    
    # 1. Verification Step (as before)
    v_params = params.copy()
    v_params["openid.mode"] = "check_authentication"
    
    async with httpx.AsyncClient() as client:
        response = await client.post(steam_openid_url, data=v_params)
    
    if "is_valid:true" not in response.text:
        raise HTTPException(status_code=400, detail="Invalid Steam login")

    # 2. Extract SteamID64
    claimed_id = params.get("openid.claimed_id", "")
    steam_id = re.search(r"id/(\d+)$", claimed_id).group(1)

    # 3. Create the JWT
    token = create_access_token(data={"sub": steam_id})

    response = RedirectResponse(url="/")
    response.set_cookie(
        key=cookie_name,
        value=token, 
        httponly=True, 
        samesite="lax", 
        secure=False # Set to False only for local development
    )
    return response

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie(
        key=cookie_name
    )
    return response

async def get_current_user(request: Request) -> str:
    token = request.cookies.get(cookie_name)
    if not token:
        return None
    
    try:
        payload = jwt.decode(token, jwt_secret_key, algorithms=[jwt.ALGORITHMS.HS256])
        steam_id: str = payload.get("sub")
        if steam_id is None:
           return None
        return steam_id
    except JWTError:
        return None

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=120)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, jwt_secret_key, algorithm=jwt.ALGORITHMS.HS256)
