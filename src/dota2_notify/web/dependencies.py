from pathlib import Path
from datetime import datetime
from fastapi import Request
from fastapi.templating import Jinja2Templates
from starlette.requests import HTTPConnection

from dota2_notify.models.user import steam_id_to_account_id

top = Path(__file__).resolve().parent
template_obj = Jinja2Templates(directory=str(top / "templates"))
template_obj.env.globals["now"] = datetime.now
template_obj.env.globals['CSS_VERSION'] = "1.0.2"
template_obj.env.filters["dotabuff_url"] = lambda steam_id: f"https://www.dotabuff.com/players/{steam_id_to_account_id(int(steam_id))}"

def get_user_service(request: Request):
    return request.app.state.user_service

def get_steam_client(request: Request):
    return request.app.state.steam_client

def get_redis_client(request: HTTPConnection):
    return request.app.state.redis_client
