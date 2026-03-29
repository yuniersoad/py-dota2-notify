from pathlib import Path
from datetime import datetime
from fastapi import Request
from fastapi.templating import Jinja2Templates

top = Path(__file__).resolve().parent
template_obj = Jinja2Templates(directory=str(top / "templates"))
template_obj.env.globals["now"] = datetime.now
template_obj.env.globals['CSS_VERSION'] = "1.0.0"

def get_user_service(request: Request):
    return request.app.state.user_service

def get_steam_client(request: Request):
    return request.app.state.steam_client