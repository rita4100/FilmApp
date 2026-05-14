"""Endpoints pro uživatele - registrace, login."""
from fastapi import APIRouter, HTTPException
from ..database import get_db  # Přístup k usersovou tabulku

router = APIRouter(tags=["users"])  # Routes pro autentizaci


@router.post("/register")
def register(payload: dict):
    """Registrace nového uživatele."""
    username = (payload.get("username") or "").strip()
    password = (payload.get("password") or "").strip()
    if not username or not password:
        raise HTTPException(status_code=400, detail="Vyplň username a heslo")
    conn = get_db()
    try:
        conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()
        return {"message": "Registrace úspěšná!"}
    except Exception:
        conn.close()
        raise HTTPException(status_code=409, detail="Username již existuje")


@router.post("/login")
def login(payload: dict):
    """Přihlášení uživatele."""
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE username=? AND password=?",
        (payload.get("username"), payload.get("password"))
    ).fetchone()
    conn.close()
    if not user:
        raise HTTPException(status_code=401, detail="Špatné přihlašovací údaje")
    if user["banned"]:
        raise HTTPException(status_code=403, detail="Účet je zablokován")
    return {"id": user["id"], "username": user["username"], "role": user["role"]}
