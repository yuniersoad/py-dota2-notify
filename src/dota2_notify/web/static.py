from fastapi.staticfiles import StaticFiles
from pathlib import Path
from fastapi.responses import FileResponse
from fastapi import APIRouter

STATIC_DIR = Path(__file__).parent / "static"

# Create static files mount
static_files = StaticFiles(directory=str(STATIC_DIR))

router = APIRouter()

@router.get("/robots.txt", response_class=FileResponse)
async def robots_txt():
    return STATIC_DIR / "robots.txt"
