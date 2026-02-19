from pathlib import Path
from fastapi.templating import Jinja2Templates

top = Path(__file__).resolve().parent
template_obj = Jinja2Templates(directory=str(top / "templates"))