from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "VLOZ_SVUJ_KLIC_SEM")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
DB_PATH = os.path.join(BASE_DIR, "films.db")
FRONTEND_DIR = os.path.join(PROJECT_DIR, "frontend")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# Serve frontend static files
app.mount("/static", StaticFiles(directory=os.path.join(FRONTEND_DIR, "static")), name="static")


@app.get("/", response_class=HTMLResponse)
def index():
    idx = os.path.join(FRONTEND_DIR, "index.html")
    if not os.path.exists(idx):
        raise HTTPException(status_code=404, detail="Frontend not found")
    return FileResponse(idx, media_type="text/html")


# Films
@app.get("/films")
def get_films(genre: str = None, year: int = None, min_rating: float = 0, sort: str = "rating", page: int = 1):
    per_page = 20
    query = "SELECT DISTINCT f.* FROM films f"
    params = []
    if genre:
        query += " JOIN film_genres fg ON f.id = fg.film_id JOIN genres g ON fg.genre_id = g.id WHERE g.name = ?"
        params.append(genre)
    else:
        query += " WHERE 1=1"

    if year:
        query += " AND f.year = ?"
        params.append(year)

    query += " AND f.rating >= ?"
    params.append(min_rating)

    allowed_sorts = {"rating": "f.rating DESC", "year": "f.year DESC", "title": "f.title ASC"}
    query += f" ORDER BY {allowed_sorts.get(sort, 'f.rating DESC')}"
    query += f" LIMIT {per_page} OFFSET {(page-1)*per_page}"

    conn = get_db()
    films = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(f) for f in films]


@app.get("/films/random")
def random_film():
    conn = get_db()
    film = conn.execute("SELECT * FROM films ORDER BY RANDOM() LIMIT 1").fetchone()
    conn.close()
    if not film:
        raise HTTPException(status_code=404, detail="No films")
    return dict(film)


@app.get("/films/top10")
def top10():
    conn = get_db()
    films = conn.execute("SELECT * FROM films ORDER BY rating DESC LIMIT 10").fetchall()
    conn.close()
    return [dict(f) for f in films]


@app.get("/films/{film_id}")
def get_film(film_id: int):
    conn = get_db()
    film = conn.execute("SELECT * FROM films WHERE id = ?", (film_id,)).fetchone()
    if not film:
        conn.close()
        raise HTTPException(status_code=404, detail="Film nenalezen")

    genres = conn.execute("""
        SELECT g.name FROM genres g
        JOIN film_genres fg ON g.id = fg.genre_id
        WHERE fg.film_id = ?
    """, (film_id,)).fetchall()

    soundtracks = conn.execute("SELECT song_title, artist FROM soundtracks WHERE film_id = ?", (film_id,)).fetchall()
    result = dict(film)
    result["genres"] = [g[0] for g in genres]
    result["soundtracks"] = [dict(s) for s in soundtracks]
    conn.close()
    return result


@app.get("/films/{film_id}/soundtrack")
def get_soundtrack(film_id: int):
    conn = get_db()
    tracks = conn.execute("SELECT * FROM soundtracks WHERE film_id = ?", (film_id,)).fetchall()
    conn.close()
    return [dict(t) for t in tracks]


# Genres
@app.get("/genres")
def get_genres():
    conn = get_db()
    genres = conn.execute("SELECT * FROM genres").fetchall()
    conn.close()
    return [dict(g) for g in genres]


# Users
@app.post("/register")
def register(payload: dict):
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


@app.post("/login")
def login(payload: dict):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username=? AND password=?",
                        (payload.get("username"), payload.get("password"))).fetchone()
    conn.close()
    if not user:
        raise HTTPException(status_code=401, detail="Špatné přihlašovací údaje")
    if user["banned"]:
        raise HTTPException(status_code=403, detail="Účet je zablokován")
    return {"id": user["id"], "username": user["username"], "role": user["role"]}


# Watchlist
@app.post("/watchlist")
def update_watchlist(payload: dict):
    user_id = payload.get("user_id")
    film_id = payload.get("film_id")
    status = payload.get("status")
    if status not in ("seen", "want", "fav", None):
        raise HTTPException(status_code=400, detail="Neplatný status")
    conn = get_db()
    if status is None:
        conn.execute("DELETE FROM watchlist WHERE user_id=? AND film_id=?", (user_id, film_id))
    else:
        conn.execute("""INSERT INTO watchlist (user_id, film_id, status) VALUES (?, ?, ?)
                        ON CONFLICT(user_id, film_id) DO UPDATE SET status=?""",
                     (user_id, film_id, status, status))
    conn.commit()
    conn.close()
    return {"message": "OK"}


@app.get("/watchlist/{user_id}")
def get_watchlist(user_id: int):
    conn = get_db()
    items = conn.execute("""
        SELECT f.*, w.status FROM films f
        JOIN watchlist w ON f.id = w.film_id
        WHERE w.user_id = ?
    """, (user_id,)).fetchall()
    conn.close()
    return [dict(i) for i in items]


# Ratings
@app.post("/ratings")
def rate_film(payload: dict):
    conn = get_db()
    conn.execute("""INSERT INTO ratings (user_id, film_id, score) VALUES (?, ?, ?)
                    ON CONFLICT(user_id, film_id) DO UPDATE SET score=?""",
                 (payload["user_id"], payload["film_id"], payload["score"], payload["score"]))
    conn.commit()
    conn.close()
    return {"message": "Hodnocení uloženo"}


# Admin
@app.get("/admin/users")
def admin_users():
    conn = get_db()
    users = conn.execute("SELECT id, username, role, banned FROM users").fetchall()
    conn.close()
    return [dict(u) for u in users]


@app.post("/admin/ban/{user_id}")
def ban_user(user_id: int, payload: dict):
    banned = 1 if payload.get("ban", True) else 0
    conn = get_db()
    conn.execute("UPDATE users SET banned=? WHERE id=?", (banned, user_id))
    conn.commit()
    conn.close()
    return {"message": "Hotovo"}


@app.post("/admin/films")
def add_film(payload: dict):
    conn = get_db()
    conn.execute("""INSERT INTO films (title, year, description, rating, poster_url)
                    VALUES (?, ?, ?, ?, ?)""",
                 (payload.get("title"), payload.get("year"), payload.get("description"),
                  payload.get("rating", 0), payload.get("poster_url", "")))
    conn.commit()
    conn.close()
    return {"message": "Film přidán"}


@app.delete("/admin/films/{film_id}")
def delete_film(film_id: int):
    conn = get_db()
    conn.execute("DELETE FROM films WHERE id=?", (film_id,))
    conn.commit()
    conn.close()
    return {"message": "Film smazán"}


# Mood match
@app.post("/mood-match")
def mood_match(payload: dict):
    mood = (payload.get("mood") or "").lower()
    words = mood.split()
    conn = get_db()
    films = conn.execute("SELECT * FROM films").fetchall()
    results = []
    for film in films:
        desc = (film["description"] or "").lower()
        title = (film["title"] or "").lower()
        score = sum(1 for w in words if w in desc or w in title)
        if score > 0:
            results.append((score, dict(film)))
    results.sort(key=lambda x: x[0], reverse=True)
    top5 = [r[1] for r in results[:5]]
    conn.close()
    return top5


# Stats
@app.get("/stats")
def stats():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) as c FROM films").fetchone()["c"]
    by_year = conn.execute("SELECT year, COUNT(*) as count FROM films GROUP BY year ORDER BY year DESC").fetchall()
    by_genre = conn.execute("""
        SELECT g.name, COUNT(*) as count FROM genres g
        JOIN film_genres fg ON g.id = fg.genre_id
        GROUP BY g.name ORDER BY count DESC LIMIT 10
    """).fetchall()
    conn.close()
    return {"total_films": total, "by_year": [dict(r) for r in by_year], "by_genre": [dict(r) for r in by_genre]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app_fastapi:app", host="0.0.0.0", port=5002, reload=True)


@app.get("/{file_path:path}")
def serve_frontend(file_path: str):
    # Serve other frontend files (html, etc.) if they exist in the frontend folder
    # This route is defined last so API routes take precedence.
    full = os.path.join(FRONTEND_DIR, file_path)
    if os.path.exists(full) and os.path.isfile(full):
        # try to set a simple content type for html and others
        if file_path.endswith('.html'):
            return FileResponse(full, media_type='text/html')
        return FileResponse(full)
    raise HTTPException(status_code=404, detail="File not found")
