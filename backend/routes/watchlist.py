"""Endpoints pro seznam filmů - chci vidět, viděl jsem, oblíbené."""
from fastapi import APIRouter, HTTPException
from ..database import get_db  # Přístup do watchlist tabulky

router = APIRouter(prefix="/watchlist", tags=["watchlist"])  # Všechny routes začínají /watchlist


@router.post("")
def update_watchlist(payload: dict):
    """Aktualizuje seznam filmů uživatele."""
    user_id = payload.get("user_id")
    film_id = payload.get("film_id")
    status = payload.get("status")
    if status not in ("seen", "want", "fav", None):
        raise HTTPException(status_code=400, detail="Neplatný status")
    conn = get_db()
    if status is None:
        conn.execute("DELETE FROM watchlist WHERE user_id=? AND film_id=?", (user_id, film_id))
    else:
        conn.execute(
            """INSERT INTO watchlist (user_id, film_id, status) VALUES (?, ?, ?)
               ON CONFLICT(user_id, film_id) DO UPDATE SET status=?""",
            (user_id, film_id, status, status)
        )
    conn.commit()
    conn.close()
    return {"message": "OK"}


@router.get("/{user_id}")
def get_watchlist(user_id: int):
    """Vrací seznam filmů uživatele."""
    conn = get_db()
    items = conn.execute(
        """SELECT f.*, w.status FROM films f
           JOIN watchlist w ON f.id = w.film_id
           WHERE w.user_id = ?""",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(i) for i in items]
