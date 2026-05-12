import requests
import sqlite3
import os
import time
from dotenv import load_dotenv
from .db import init_db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "films.db")

# ⚠️ VLOŽ SVŮJ TMDB KLÍČ SEM
load_dotenv()
# Configurable via env vars:
# SEED_PAGES - number of TMDB pages to fetch (default 8 -> ~160 films)
# SEED_SLEEP - seconds to sleep between page requests (default 0.3)
SEED_PAGES = int(os.environ.get("SEED_PAGES", "8"))
SEED_SLEEP = float(os.environ.get("SEED_SLEEP", "0.3"))

TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "508944053824398b6bbf87dda02bc4e4")
BASE_URL = "https://api.themoviedb.org/3"

def fetch_movies(page=1, attempts=3, sleep_sec=SEED_SLEEP):
    """
    Fetch a page from TMDB with simple retry/backoff logic for transient errors (429/5xx).
    """
    url = f"{BASE_URL}/movie/popular?api_key={TMDB_API_KEY}&language=cs-CZ&page={page}"
    for attempt in range(1, attempts + 1):
        try:
            resp = requests.get(url, timeout=10)
        except Exception as e:
            print(f"⚠️ Chyba připojení při volání TMDB (attempt {attempt}): {e}")
            if attempt < attempts:
                time.sleep(sleep_sec * (2 ** (attempt-1)))
                continue
            return []

        if resp.status_code == 200:
            return resp.json().get("results", [])
        if resp.status_code == 429:
            # Rate limited; wait and retry with exponential backoff
            wait = sleep_sec * (2 ** (attempt-1))
            print(f"⏳ TMDB rate limit (429), čekám {wait}s a zkusím to znovu...")
            time.sleep(wait)
            continue
        if 500 <= resp.status_code < 600:
            # Server error, retry
            wait = sleep_sec * (2 ** (attempt-1))
            print(f"⚠️ TMDB server error {resp.status_code}, čekám {wait}s (attempt {attempt})")
            time.sleep(wait)
            continue

        # other client error - likely bad API key or bad request
        print(f"❌ Chyba TMDB API: {resp.status_code} - zkontroluj API klíč nebo request")
        return []

    return []

def fetch_trailer(tmdb_id):
    url = f"{BASE_URL}/movie/{tmdb_id}/videos?api_key={TMDB_API_KEY}"
    resp = requests.get(url).json()
    for v in resp.get("results", []):
        if v["type"] == "Trailer" and v["site"] == "YouTube":
            return v["key"]
    return None

def fetch_genres():
    url = f"{BASE_URL}/genre/movie/list?api_key={TMDB_API_KEY}&language=cs-CZ"
    resp = requests.get(url).json()
    return {g["id"]: g["name"] for g in resp.get("genres", [])}

def seed():
    init_db()  # nejdřív vytvoř tabulky
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    print("📥 Stahuji žánry...")
    genres = fetch_genres()
    for gid, gname in genres.items():
        c.execute("INSERT OR IGNORE INTO genres (id, name) VALUES (?, ?)", (gid, gname))

    print(f"📥 Stahuji filmy z TMDB ({SEED_PAGES} stránek = ~{SEED_PAGES*20} filmů)...")
    for page in range(1, SEED_PAGES + 1):
        movies = fetch_movies(page)
        for movie in movies:
            trailer = fetch_trailer(movie["id"])
            poster = ""
            if movie.get("poster_path"):
                poster = "https://image.tmdb.org/t/p/w500" + movie["poster_path"]

            c.execute("""INSERT OR IGNORE INTO films 
                (tmdb_id, title, year, description, rating, poster_url, trailer_key)
                VALUES (?, ?, ?, ?, ?, ?, ?)""", (
                movie["id"],
                movie.get("title", ""),
                (movie.get("release_date", "0000"))[:4],
                movie.get("overview", ""),
                movie.get("vote_average", 0),
                poster,
                trailer
            ))
            
            # Přiřaď žánry
            film_id = c.lastrowid or c.execute("SELECT id FROM films WHERE tmdb_id=?", (movie["id"],)).fetchone()[0]
            for gid in movie.get("genre_ids", []):
                c.execute("INSERT OR IGNORE INTO film_genres VALUES (?, ?)", (film_id, gid))

    print(f"  ✅ Stránka {page} hotová")
    # Be polite to the API — small pause between pages
    time.sleep(SEED_SLEEP)

    conn.commit()
    conn.close()
    print("🎉 Databáze naplněna filmy!")

if __name__ == "__main__":
    seed()
