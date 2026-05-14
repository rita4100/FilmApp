# FastAPI backend pro jednoduchou filmovou aplikaci.
# Obsahuje API, databázi a obsluhu frontendových statických souborů.
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import os
from dotenv import load_dotenv
from .db import init_db
from .seed import seed as seed_db, TMDB_API_KEY as SEED_TMDB_API_KEY
import requests

load_dotenv()

# Používáme env proměnnou TMDB_API_KEY, jinak fallback na seed klíč.
TMDB_API_KEY = os.environ.get("TMDB_API_KEY") or SEED_TMDB_API_KEY
if not os.environ.get("TMDB_API_KEY"):
    print("TMDB_API_KEY nebyl nalezen v prostredi. Pouzivam zalohovaci klic ze seed.py.")
BASE_URL = "https://api.themoviedb.org/3"
MUSICBRAINZ_BASE = "https://musicbrainz.org/ws/2"
MUSICBRAINZ_USER_AGENT = os.environ.get("MUSICBRAINZ_USER_AGENT", "MovieMind/1.0.0 (info@moviemind.local)")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
DB_PATH = os.path.join(BASE_DIR, "films.db")
FRONTEND_DIR = os.path.join(PROJECT_DIR, "frontend")

app = FastAPI()


# Inicializace databáze při startu aplikace.
init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Připojení k SQLite databázi.
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# Kontrola, zda databáze již obsahuje filmy.
def has_films():
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM films").fetchone()[0]
    conn.close()
    return count > 0


# Při startu aplikace naplní databázi, pokud je prázdná.
@app.on_event("startup")
async def seed_database_if_empty():
    if not has_films():
        print("ℹ️ Databáze je prázdná, naplňuji filmy...")
        try:
            seed_db()
        except Exception as e:
            print("⚠️ Nepodařilo se naplnit databázi:", e)


# Omezení délky textu pro vyhledávání (ochrana před příliš dlouhými dotazy).
SEARCH_MAX_LEN = 200


def normalize_search_q(q: str | None) -> str | None:
    if q is None:
        return None
    s = q.strip()
    if not s:
        return None
    if len(s) > SEARCH_MAX_LEN:
        s = s[:SEARCH_MAX_LEN]
    return s.lower()


# Pomocné funkce pro validaci číselného hodnocení.
def parse_rating(value, default=0):
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        raise HTTPException(status_code=400, detail="Hodnocení musí být celé číslo od 0 do 10")
    try:
        score = int(value)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Hodnocení musí být celé číslo od 0 do 10")
    if score < 0 or score > 10:
        raise HTTPException(status_code=400, detail="Hodnocení musí být celé číslo od 0 do 10")
    return score


# Validuje uživatelské hodnocení (1-10).
def parse_user_rating(value):
    score = parse_rating(value, default=None)
    if score is None or score < 1:
        raise HTTPException(status_code=400, detail="Hodnocení musí být celé číslo od 1 do 10")
    return score


# Volání TMDB pro načtení cast & crew dat.
def fetch_tmdb_credits(tmdb_id: int):
    if not TMDB_API_KEY or TMDB_API_KEY.startswith("VLOZ"):
        print("Nebyl k dispozici platny TMDB API klic. Nelze nacist herce a stab.")
        return None
    try:
        resp = requests.get(f"{BASE_URL}/movie/{tmdb_id}/credits", params={"api_key": TMDB_API_KEY, "language": "cs-CZ"}, timeout=10)
        if resp.status_code != 200:
            print(f"⚠️ TMDB credits request failed: {resp.status_code} {resp.text}")
            return None
        return resp.json()
    except Exception as exc:
        print(f"⚠️ Chyba při načítání TMDB credits: {exc}")
        return None


def fetch_tmdb_external_ids(tmdb_id: int):
    if not TMDB_API_KEY or TMDB_API_KEY.startswith("VLOZ"):
        return None
    try:
        resp = requests.get(f"{BASE_URL}/movie/{tmdb_id}/external_ids", params={"api_key": TMDB_API_KEY}, timeout=10)
        if resp.status_code != 200:
            print(f"⚠️ TMDB external_ids request failed: {resp.status_code} {resp.text}")
            return None
        return resp.json()
    except Exception as exc:
        print(f"⚠️ Chyba při načítání TMDB external IDs: {exc}")
        return None


def fetch_tmdb_movie_details(tmdb_id: int):
    if not TMDB_API_KEY or TMDB_API_KEY.startswith("VLOZ"):
        return None
    try:
        resp = requests.get(f"{BASE_URL}/movie/{tmdb_id}", params={"api_key": TMDB_API_KEY, "language": "en-US"}, timeout=10)
        if resp.status_code != 200:
            print(f"⚠️ TMDB movie details request failed: {resp.status_code} {resp.text}")
            return None
        return resp.json()
    except Exception as exc:
        print(f"⚠️ Chyba při načítání TMDB movie details: {exc}")
        return None


# Volání MusicBrainz API pro soundtracky.
def musicbrainz_get(path: str, params: dict):
    try:
        resp = requests.get(f"{MUSICBRAINZ_BASE}/{path}", params=params, headers={"User-Agent": MUSICBRAINZ_USER_AGENT}, timeout=10)
        if resp.status_code != 200:
            print(f"⚠️ MusicBrainz request failed: {resp.status_code} {resp.text}")
            return None
        return resp.json()
    except Exception as exc:
        print(f"⚠️ Chyba při načítání MusicBrainz: {exc}")
        return None


# Hledá release podle IMDb nebo názvu filmu.
def search_musicbrainz_release(imdb_id: str = None, title: str = None, year: int = None):
    query = None
    if imdb_id:
        query = f'imdbid:"{imdb_id}" AND secondarytype:Soundtrack'
    elif title:
        safe_title = title.replace('"', '')
        query = f'"{safe_title}" AND secondarytype:Soundtrack'
        if year:
            query += f" AND date:{year}"
    else:
        return None

    data = musicbrainz_get("release", {"query": query, "fmt": "json", "limit": 10})
    if not data:
        return None
    releases = data.get("releases") or []
    return releases[0] if releases else None


def fetch_musicbrainz_release_tracks(release_id: str):
    data = musicbrainz_get(f"release/{release_id}", {"inc": "recordings", "fmt": "json"})
    if not data:
        return None

    artist_credit = data.get("artist-credit") or []
    default_artist = ''.join([str(item.get("name", "")) for item in artist_credit if item])
    tracks = []
    for medium in data.get("media", []):
        for track in medium.get("tracks", []):
            artist_name = ''
            track_artist_credit = track.get("artist-credit") or []
            if track_artist_credit:
                artist_name = ''.join([str(item.get("name", "")) for item in track_artist_credit if item])
            if not artist_name:
                artist_name = default_artist
            title = track.get('title', '') or ''
            tracks.append({
                "song_title": title.strip(),
                "artist": artist_name
            })
    return tracks


def enrich_soundtracks_with_musicbrainz(film_id: int, title: str, tmdb_id: int = None):
    imdb_id = None
    tmdb_original_title = None
    tmdb_year = None

    if tmdb_id:
        external = fetch_tmdb_external_ids(tmdb_id)
        imdb_id = external.get("imdb_id") if external else None
        details = fetch_tmdb_movie_details(tmdb_id)
        if details:
            tmdb_original_title = details.get("original_title")
            tmdb_year = details.get("release_date", "")[:4] if details.get("release_date") else None

    release = None
    if imdb_id:
        release = search_musicbrainz_release(imdb_id=imdb_id, year=tmdb_year)
    if not release and tmdb_original_title and tmdb_original_title != title:
        release = search_musicbrainz_release(title=tmdb_original_title, year=tmdb_year)
    if not release:
        release = search_musicbrainz_release(title=title, year=tmdb_year)
    if not release and tmdb_original_title and tmdb_original_title != title:
        release = search_musicbrainz_release(title=tmdb_original_title)
    if not release:
        release = search_musicbrainz_release(title=title)
    if not release:
        return []

    tracks = fetch_musicbrainz_release_tracks(release.get("id"))
    if not tracks:
        return []

    conn = get_db()
    conn.execute("DELETE FROM soundtracks WHERE film_id = ?", (film_id,))
    for track in tracks:
        conn.execute("INSERT INTO soundtracks (film_id, song_title, artist) VALUES (?, ?, ?)",
                     (film_id, track["song_title"], track["artist"]))
    conn.commit()
    conn.close()
    return tracks


def save_credits(film_id: int, credits: dict):
    if not credits:
        return
    conn = get_db()
    conn.execute("DELETE FROM credits WHERE film_id = ?", (film_id,))
    for cast_member in credits.get("cast", []):
        conn.execute("""INSERT INTO credits (film_id, role_type, person_name, character, job, department, credit_order)
                        VALUES (?, 'cast', ?, ?, ?, ?, ?)""",
                     (film_id, cast_member.get("name"), cast_member.get("character"), None,
                      cast_member.get("known_for_department"), cast_member.get("order", 0)))
    for crew_member in credits.get("crew", []):
        conn.execute("""INSERT INTO credits (film_id, role_type, person_name, character, job, department, credit_order)
                        VALUES (?, 'crew', ?, ?, ?, ?, ?)""",
                     (film_id, crew_member.get("name"), None, crew_member.get("job"),
                      crew_member.get("department"), crew_member.get("order", 0)))
    conn.commit()
    conn.close()


def get_credits(film_id: int, tmdb_id: int = None):
    conn = get_db()
    rows = conn.execute("""SELECT role_type, person_name, character, job, department, credit_order
                          FROM credits
                          WHERE film_id = ?
                          ORDER BY role_type, credit_order""", (film_id,)).fetchall()
    conn.close()
    if rows:
        cast = []
        crew = []
        for row in rows:
            if row[0] == 'cast':
                cast.append({"person_name": row[1], "character": row[2], "order": row[5]})
            else:
                crew.append({"person_name": row[1], "job": row[3], "department": row[4], "order": row[5]})
        return {"cast": cast, "crew": crew}

    if tmdb_id:
        credits = fetch_tmdb_credits(tmdb_id)
        if credits:
            save_credits(film_id, credits)
            return get_credits(film_id)
    return {"cast": [], "crew": []}


# Serve frontend statické soubory a hlavní HTML stránku.
app.mount("/static", StaticFiles(directory=os.path.join(FRONTEND_DIR, "static")), name="static")


@app.get("/", response_class=HTMLResponse)
def index():
    idx = os.path.join(FRONTEND_DIR, "index.html")
    if not os.path.exists(idx):
        raise HTTPException(status_code=404, detail="Frontend not found")
    return FileResponse(idx, media_type="text/html")


# Films
# Vrací seznam filmů s filtrováním, řazením a stránkováním.
@app.get("/films")
def get_films(genre: str = None, year: int = None, rating: int = None, min_rating: int = 0, sort: str = "rating", page: int = 1, q: str = None):
    per_page = 20
    query = "SELECT DISTINCT f.id, f.title, f.year, f.description, f.rating, f.poster_url, f.trailer_key FROM films f"
    params = []
    if genre:
        query += " JOIN film_genres fg ON f.id = fg.film_id JOIN genres g ON fg.genre_id = g.id WHERE g.name = ?"
        params.append(genre)
    else:
        query += " WHERE 1=1"

    if year:
        query += " AND f.year = ?"
        params.append(year)

    if rating is not None:
        query += " AND f.rating >= ? AND f.rating < ?"
        params.append(rating)
        params.append(rating + 1)
    else:
        query += " AND f.rating >= ?"
        params.append(min_rating)

    needle = normalize_search_q(q)
    if needle:
        query += " AND (instr(lower(f.title), ?) > 0 OR instr(lower(coalesce(f.description, '')), ?) > 0)"
        params.append(needle)
        params.append(needle)

    allowed_sorts = {"rating": "f.rating DESC", "year": "f.year DESC", "title": "f.title ASC"}
    query += f" ORDER BY {allowed_sorts.get(sort, 'f.rating DESC')}"
    query += f" LIMIT {per_page} OFFSET {(page-1)*per_page}"

    conn = get_db()
    films = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(f) for f in films]


# Vrací náhodně vybraný film z databáze.
@app.get("/films/random")
def random_film():
    conn = get_db()
    film = conn.execute("SELECT id, title, year, description, rating, poster_url, trailer_key FROM films ORDER BY RANDOM() LIMIT 1").fetchone()
    conn.close()
    if not film:
        raise HTTPException(status_code=404, detail="No films")
    return dict(film)


# Vrací Top 10 filmů podle hodnocení, volitelně filtrováno žánrem a rokem.
@app.get("/films/top10")
def top10(genre: str = None, year: int = None):
    # Support optional filtering by genre and year
    conn = get_db()
    query = "SELECT DISTINCT f.id, f.title, f.year, f.description, f.rating, f.poster_url, f.trailer_key FROM films f"
    params = []
    if genre:
        query += " JOIN film_genres fg ON f.id = fg.film_id JOIN genres g ON fg.genre_id = g.id WHERE g.name = ?"
        params.append(genre)
    else:
        query += " WHERE 1=1"

    if year:
        query += " AND f.year = ?"
        params.append(year)

    query += " ORDER BY f.rating DESC LIMIT 10"

    films = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(f) for f in films]


# Jednoduchý filtr filmů podle minimálního hodnocení.
@app.get("/films/filter")
def filter_films(min_rating: int):
    if not isinstance(min_rating, int) or isinstance(min_rating, bool):
        raise HTTPException(status_code=400, detail="min_rating must be an integer from 0 to 10")
    if min_rating < 0 or min_rating > 10:
        raise HTTPException(status_code=400, detail="min_rating must be an integer from 0 to 10")

    conn = get_db()
    films = conn.execute(
        "SELECT * FROM films WHERE rating >= ? ORDER BY rating DESC",
        (min_rating,)
    ).fetchall()
    conn.close()
    return [dict(f) for f in films]


# Vrací detailní informace o jednom filmu, včetně žánrů, soundtracků, castu a komunitních recenzí.
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
    rating_stats = conn.execute("SELECT AVG(score) AS avg_score, COUNT(*) AS review_count FROM ratings WHERE film_id = ?", (film_id,)).fetchone()
    recent_reviews = conn.execute("""SELECT r.score, r.comment, r.created_at, r.updated_at, r.user_id, u.username
                                     FROM ratings r
                                     JOIN users u ON u.id = r.user_id
                                     WHERE r.film_id = ?
                                     ORDER BY r.updated_at DESC
                                     LIMIT 10""", (film_id,)).fetchall()

    result = dict(film)
    result["genres"] = [g[0] for g in genres]
    result["soundtracks"] = [dict(s) for s in soundtracks]
    credits = get_credits(film_id, result.get("tmdb_id"))
    result["cast"] = credits["cast"][:12]
    result["crew"] = credits["crew"][:10]
    result["community_rating"] = round(rating_stats["avg_score"], 1) if rating_stats["avg_score"] is not None else None
    result["review_count"] = rating_stats["review_count"]
    result["reviews"] = [dict(r) for r in recent_reviews]
    conn.close()
    return result


@app.get("/films/{film_id}/soundtrack")
def get_soundtrack(film_id: int):
    conn = get_db()
    tracks = conn.execute("SELECT * FROM soundtracks WHERE film_id = ?", (film_id,)).fetchall()
    if tracks:
        conn.close()
        return [dict(t) for t in tracks]

    film = conn.execute("SELECT title, tmdb_id FROM films WHERE id = ?", (film_id,)).fetchone()
    conn.close()
    if not film:
        raise HTTPException(status_code=404, detail="Film nenalezen")

    result = enrich_soundtracks_with_musicbrainz(film_id, film["title"], film["tmdb_id"])
    if result:
        return result
    return [{"song_title": "Soundtrack nebyl nalezen.", "artist": ""}]


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
    user_id = payload.get("user_id")
    film_id = payload.get("film_id")
    if not user_id or not film_id:
        raise HTTPException(status_code=400, detail="Chybí user_id nebo film_id")
    score = parse_user_rating(payload.get("score"))
    comment = payload.get("comment") or ""
    conn = get_db()
    conn.execute("""INSERT INTO ratings (user_id, film_id, score, comment)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(user_id, film_id) DO UPDATE SET
                      score = excluded.score,
                      comment = excluded.comment,
                      updated_at = CURRENT_TIMESTAMP""",
                 (user_id, film_id, score, comment))
    conn.commit()
    conn.close()
    return {"message": "Hodnocení uloženo"}

@app.get("/ratings")
def get_ratings(film_id: int, user_id: int = None):
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
    rating = parse_rating(payload.get("rating", 0))
    conn = get_db()
    conn.execute("""INSERT INTO films (title, year, description, rating, poster_url)
                    VALUES (?, ?, ?, ?, ?)""",
                 (payload.get("title"), payload.get("year"), payload.get("description"),
                  rating, payload.get("poster_url", "")))
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
    uvicorn.run("backend.app_fastapi:app", host="0.0.0.0", port=5002, reload=True)


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
