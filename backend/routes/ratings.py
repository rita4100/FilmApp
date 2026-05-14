"""Endpoints pro hodŽnocení a recenze filmů."""
from fastapi import APIRouter, HTTPException
from ..database import get_db  # Přístup do ratings tabulky
from ..validators import parse_user_rating  # Validace hodŽnocení 1-10

router = APIRouter(prefix="/ratings", tags=["ratings"])  # Všechny routes začínají /ratings


@router.post("")
def rate_film(payload: dict):
    """Přidá nebo aktualizuje hodnocení filmu."""
    user_id = payload.get("user_id")
    film_id = payload.get("film_id")
    if not user_id or not film_id:
        raise HTTPException(status_code=400, detail="Chybí user_id nebo film_id")
    score = parse_user_rating(payload.get("score"))
    comment = payload.get("comment") or ""
    conn = get_db()
    conn.execute(
        """INSERT INTO ratings (user_id, film_id, score, comment)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(user_id, film_id) DO UPDATE SET
             score = excluded.score,
             comment = excluded.comment,
             updated_at = CURRENT_TIMESTAMP""",
        (user_id, film_id, score, comment)
    )
    conn.commit()
    conn.close()
    return {"message": "Hodnocení uloženo"}


@router.get("")
def get_ratings(film_id: int, user_id: int = None):
    """Vrací recenze k filmu."""
    conn = get_db()
    query = """SELECT r.score, r.comment, r.created_at, r.updated_at, r.user_id, u.username
               FROM ratings r
               JOIN users u ON u.id = r.user_id
               WHERE r.film_id = ?"""
    params = [film_id]
    if user_id:
        query += " AND r.user_id = ?"
        params.append(user_id)
    reviews = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in reviews]
