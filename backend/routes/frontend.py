"""Endpoints pro obslugu frontendých souborů - HTML, statické soubory."""
import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from ..config import FRONTEND_DIR  # Cesta k frontend adresáři

router = APIRouter(tags=["frontend"])  # Routes pro obsluhu statických souborů


@router.get("/", response_class=HTMLResponse)
def index():
    """Vrací hlavní stránku aplikace."""
    idx = os.path.join(FRONTEND_DIR, "index.html")
    if not os.path.exists(idx):
        raise HTTPException(status_code=404, detail="Frontend not found")
    return FileResponse(idx, media_type="text/html")


@router.get("/{file_path:path}")
def serve_frontend(file_path: str):
    """Vrací ostatní frontendové soubory (HTML, atd.)."""
    full = os.path.join(FRONTEND_DIR, file_path)
    if os.path.exists(full) and os.path.isfile(full):
        if file_path.endswith('.html'):
            return FileResponse(full, media_type='text/html')
        return FileResponse(full)
    raise HTTPException(status_code=404, detail="File not found")
