from fastapi.staticfiles import StaticFiles
from pathlib import Path

STATIC_DIR = Path(__file__).parent / "static"

# Create static files mount
static_files = StaticFiles(directory=str(STATIC_DIR))
