"""Endpoints pro žánry."""
from fastapi import APIRouter
from ..database import get_db

router = APIRouter(prefix="/genres", tags=["genres"])


@router.get("")
def get_genres():
    """Vrací seznam všech žánrů."""
    conn = get_db()
    genres = conn.execute("SELECT * FROM genres").fetchall()
    conn.close()
    return [dict(g) for g in genres]
