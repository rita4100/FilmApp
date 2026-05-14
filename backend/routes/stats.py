"""Endpoints pro statistiku."""
from fastapi import APIRouter
from ..database import get_db

router = APIRouter(tags=["stats"])


@router.get("/stats")
def stats():
    """Vrací statistiku filmů."""
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) as c FROM films").fetchone()["c"]
    by_year = conn.execute("SELECT year, COUNT(*) as count FROM films GROUP BY year ORDER BY year DESC").fetchall()
    by_genre = conn.execute(
        """SELECT g.name, COUNT(*) as count FROM genres g
           JOIN film_genres fg ON g.id = fg.genre_id
           GROUP BY g.name ORDER BY count DESC LIMIT 10"""
    ).fetchall()
    conn.close()
    return {"total_films": total, "by_year": [dict(r) for r in by_year], "by_genre": [dict(r) for r in by_genre]}
