import requests
import sqlite3
import os
from dotenv import load_dotenv
from db import init_db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "films.db")

# ⚠️ VLOŽ SVŮJ TMDB KLÍČ SEM
load_dotenv()
TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "508944053824398b6bbf87dda02bc4e4")
BASE_URL = "https://api.themoviedb.org/3"

def fetch_movies(page=1):
    url = f"{BASE_URL}/movie/popular?api_key={TMDB_API_KEY}&language=cs-CZ&page={page}"
    resp = requests.get(url)
    if resp.status_code != 200:
        print(f"❌ Chyba TMDB API: {resp.status_code} - zkontroluj API klíč!")
        return []
    return resp.json().get("results", [])

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

    print("📥 Stahuji filmy z TMDB (3 stránky = ~60 filmů)...")
    for page in range(1, 4):
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

    conn.commit()
    conn.close()
    print("🎉 Databáze naplněna filmy!")

if __name__ == "__main__":
    seed()
