"""Endpoints pro administraci - správa uživatelů a filmů."""
from fastapi import APIRouter, HTTPException
from ..database import get_db  # Přístup do databáze
from ..validators import parse_rating  # Validace hodŽnocení

router = APIRouter(prefix="/admin", tags=["admin"])  # Všechny routes začínají /admin


@router.get("/users")
def admin_users():
    """Vrací seznam všech uživatelů."""
    conn = get_db()
    users = conn.execute("SELECT id, username, role, banned FROM users").fetchall()
    conn.close()
    return [dict(u) for u in users]


@router.post("/ban/{user_id}")
def ban_user(user_id: int, payload: dict):
    """Blokuje nebo odblokuje uživatele."""
    banned = 1 if payload.get("ban", True) else 0
    conn = get_db()
    conn.execute("UPDATE users SET banned=? WHERE id=?", (banned, user_id))
    conn.commit()
    conn.close()
    return {"message": "Hotovo"}


@router.post("/films")
def add_film(payload: dict):
    """Přidá nový film do databáze."""
    rating = parse_rating(payload.get("rating", 0))
    conn = get_db()
    conn.execute(
        """INSERT INTO films (title, year, description, rating, poster_url)
           VALUES (?, ?, ?, ?, ?)""",
        (payload.get("title"), payload.get("year"), payload.get("description"),
         rating, payload.get("poster_url", ""))
    )
    conn.commit()
    conn.close()
    return {"message": "Film přidán"}


@router.delete("/films/{film_id}")
def delete_film(film_id: int):
    """Smaže film z databáze."""
    conn = get_db()
    conn.execute("DELETE FROM films WHERE id=?", (film_id,))
    conn.commit()
    conn.close()
    return {"message": "Film smazán"}
