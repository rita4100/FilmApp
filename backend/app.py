from flask import Flask, jsonify, request, send_from_directory, abort
from flask_cors import CORS
import sqlite3
import os
import requests
from dotenv import load_dotenv


app = Flask(__name__)
CORS(app)

load_dotenv()

TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "VLOZ_SVUJ_KLIC_SEM")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
DB_PATH = os.path.join(BASE_DIR, "films.db")
FRONTEND_DIR = os.path.join(PROJECT_DIR, "frontend")


@app.route("/", methods=["GET"])
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")

# ─── DB helper ────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ─── FILMY ────────────────────────────────────────────────────────────────────

@app.route("/films", methods=["GET"])
def get_films():
    genre    = request.args.get("genre")
    year     = request.args.get("year")
    try:
        min_r = float(request.args.get("min_rating", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid min_rating"}), 400
    sort_by  = request.args.get("sort", "rating")   # rating / year / title
    order    = request.args.get("order", "desc").lower()  # asc / desc
    page     = int(request.args.get("page", 1))
    per_page = 20

    query  = "SELECT DISTINCT f.* FROM films f"
    params = []

    if genre:
        query += " JOIN film_genres fg ON f.id = fg.film_id JOIN genres g ON fg.genre_id = g.id WHERE g.name = ?"
        params.append(genre)
    else:
        query += " WHERE 1=1"

    if year:
        # ensure numeric year
        try:
            y = int(year)
            if y < 0:
                return jsonify({"error": "Year cannot be negative"}), 400
        except ValueError:
            return jsonify({"error": "Invalid year"}), 400
        query += " AND f.year = ?"
        params.append(y)

    if min_r < 0:
        return jsonify({"error": "min_rating cannot be negative"}), 400

    query += " AND f.rating >= ?"
    params.append(min_r)

    # build ORDER BY with direction
    order_sql = "ASC" if order == "asc" else "DESC"
    if sort_by == "rating":
        sort_expr = f"f.rating {order_sql}"
    elif sort_by == "year":
        sort_expr = f"CAST(f.year AS INTEGER) {order_sql}"
    elif sort_by == "title":
        sort_expr = f"f.title COLLATE NOCASE {order_sql}"
    else:
        sort_expr = f"f.rating DESC"
    query += f" ORDER BY {sort_expr}"
    query += f" LIMIT {per_page} OFFSET {(page-1)*per_page}"

    conn = get_db()
    films = conn.execute(query, params).fetchall()
    conn.close()
    return jsonify([dict(f) for f in films])

@app.route("/films/random", methods=["GET"])
def random_film():
    # allow optional filters so random film is chosen from a constrained set
    genre = request.args.get("genre")
    year  = request.args.get("year")
    try:
        min_r = float(request.args.get("min_rating", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid min_rating"}), 400

    query = "SELECT DISTINCT f.* FROM films f"
    params = []
    if genre:
        query += " JOIN film_genres fg ON f.id = fg.film_id JOIN genres g ON fg.genre_id = g.id WHERE g.name = ?"
        params.append(genre)
    else:
        query += " WHERE 1=1"

    if year:
        try:
            y = int(year)
            if y < 0:
                return jsonify({"error": "Year cannot be negative"}), 400
        except ValueError:
            return jsonify({"error": "Invalid year"}), 400
        query += " AND f.year = ?"
        params.append(y)

    if min_r < 0:
        return jsonify({"error": "min_rating cannot be negative"}), 400

    query += " AND f.rating >= ?"
    params.append(min_r)

    query += " ORDER BY RANDOM() LIMIT 1"
    conn = get_db()
    film = conn.execute(query, params).fetchone()
    conn.close()
    if not film:
        return jsonify({}), 404
    return jsonify(dict(film))

@app.route("/films/top10", methods=["GET"])
def top10():
    conn = get_db()
    films = conn.execute("SELECT * FROM films ORDER BY rating DESC LIMIT 10").fetchall()
    conn.close()
    return jsonify([dict(f) for f in films])

@app.route("/films/<int:film_id>", methods=["GET"])
def get_film(film_id):
    conn = get_db()
    film = conn.execute("SELECT * FROM films WHERE id = ?", (film_id,)).fetchone()
    if not film:
        return jsonify({"error": "Film nenalezen"}), 404
    
    genres = conn.execute("""
        SELECT g.name FROM genres g
        JOIN film_genres fg ON g.id = fg.genre_id
        WHERE fg.film_id = ?
    """, (film_id,)).fetchall()
    
    soundtracks = conn.execute(
        "SELECT song_title, artist FROM soundtracks WHERE film_id = ?", (film_id,)
    ).fetchall()

    result = dict(film)
    result["genres"] = [g["name"] for g in genres]
    result["soundtracks"] = [dict(s) for s in soundtracks]
    conn.close()
    return jsonify(result)

@app.route("/films/<int:film_id>/soundtrack", methods=["GET"])
def get_soundtrack(film_id):
    conn = get_db()
    tracks = conn.execute(
        "SELECT * FROM soundtracks WHERE film_id = ?", (film_id,)
    ).fetchall()
    conn.close()
    return jsonify([dict(t) for t in tracks])

# ─── ŽÁNRY ────────────────────────────────────────────────────────────────────

@app.route("/genres", methods=["GET"])
def get_genres():
    conn = get_db()
    genres = conn.execute("SELECT * FROM genres").fetchall()
    conn.close()
    return jsonify([dict(g) for g in genres])


@app.route("/options", methods=["GET"])
def get_options():
    """Return available years and rating steps for building UI selects."""
    conn = get_db()
    years = conn.execute("SELECT DISTINCT year FROM films WHERE year IS NOT NULL ORDER BY CAST(year AS INTEGER) ASC").fetchall()
    min_year = None
    if years:
        years_list = [int(r["year"]) for r in years if r["year"] and str(r["year"]).isdigit()]
        if years_list:
            min_year = min(years_list)
    ratings = conn.execute("SELECT MIN(rating) as min_r, MAX(rating) as max_r FROM films").fetchone()
    conn.close()
    min_r = ratings["min_r"] if ratings and ratings["min_r"] is not None else 0
    max_r = ratings["max_r"] if ratings and ratings["max_r"] is not None else 10
    # create rating choices with step 0.5 (or 0.1 if needed)
    step = 0.5
    r_choices = []
    cur = float(min_r)
    # ensure sensible lower bound: not less than 0
    if cur < 0:
        cur = 0.0
    while cur <= float(max_r):
        r_choices.append(round(cur, 1))
        cur += step
    return jsonify({"years": sorted(list(set([r["year"] for r in years if r["year"] and str(r["year"]).isdigit()] or []))),
                    "min_year": min_year,
                    "ratings": r_choices,
                    "rating_min": max(0, round(float(min_r), 1)),
                    "rating_max": round(float(max_r), 1)})


@app.route("/search", methods=["GET"])
def search_films():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])
    conn = get_db()
    # simple search in title and description
    like = f"%{q}%"
    films = conn.execute("SELECT * FROM films WHERE title LIKE ? OR description LIKE ? ORDER BY year DESC LIMIT 50", (like, like)).fetchall()
    conn.close()
    return jsonify([dict(f) for f in films])

# ─── USERS ────────────────────────────────────────────────────────────────────

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    if not username or not password:
        return jsonify({"error": "Vyplň username a heslo"}), 400
    
    conn = get_db()
    try:
        conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()
        return jsonify({"message": "Registrace úspěšná!"})
    except:
        conn.close()
        return jsonify({"error": "Username již existuje"}), 409

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE username=? AND password=?",
        (data.get("username"), data.get("password"))
    ).fetchone()
    conn.close()
    if not user:
        return jsonify({"error": "Špatné přihlašovací údaje"}), 401
    if user["banned"]:
        return jsonify({"error": "Účet je zablokován"}), 403
    return jsonify({"id": user["id"], "username": user["username"], "role": user["role"]})

# ─── WATCHLIST ────────────────────────────────────────────────────────────────

@app.route("/watchlist", methods=["POST"])
def update_watchlist():
    data = request.json
    user_id = data.get("user_id")
    film_id = data.get("film_id")
    status  = data.get("status")  # seen / want / fav

    if status not in ("seen", "want", "fav", None):
        return jsonify({"error": "Neplatný status"}), 400

    conn = get_db()
    if status is None:
        conn.execute("DELETE FROM watchlist WHERE user_id=? AND film_id=?", (user_id, film_id))
    else:
        conn.execute("""INSERT INTO watchlist (user_id, film_id, status) VALUES (?, ?, ?)
                        ON CONFLICT(user_id, film_id) DO UPDATE SET status=?""",
                     (user_id, film_id, status, status))
    conn.commit()
    conn.close()
    return jsonify({"message": "OK"})

@app.route("/watchlist/<int:user_id>", methods=["GET"])
def get_watchlist(user_id):
    conn = get_db()
    items = conn.execute("""
        SELECT f.*, w.status FROM films f
        JOIN watchlist w ON f.id = w.film_id
        WHERE w.user_id = ?
    """, (user_id,)).fetchall()
    conn.close()
    return jsonify([dict(i) for i in items])

# ─── HODNOCENÍ ────────────────────────────────────────────────────────────────

@app.route("/ratings", methods=["POST"])
def rate_film():
    data = request.json
    conn = get_db()
    conn.execute("""INSERT INTO ratings (user_id, film_id, score) VALUES (?, ?, ?)
                    ON CONFLICT(user_id, film_id) DO UPDATE SET score=?""",
                 (data["user_id"], data["film_id"], data["score"], data["score"]))
    conn.commit()
    conn.close()
    return jsonify({"message": "Hodnocení uloženo"})

# ─── ADMIN ────────────────────────────────────────────────────────────────────

@app.route("/admin/users", methods=["GET"])
def admin_users():
    conn = get_db()
    users = conn.execute("SELECT id, username, role, banned FROM users").fetchall()
    conn.close()
    return jsonify([dict(u) for u in users])

@app.route("/admin/ban/<int:user_id>", methods=["POST"])
def ban_user(user_id):
    data = request.json
    banned = 1 if data.get("ban", True) else 0
    conn = get_db()
    conn.execute("UPDATE users SET banned=? WHERE id=?", (banned, user_id))
    conn.commit()
    conn.close()
    return jsonify({"message": "Hotovo"})

@app.route("/admin/films", methods=["POST"])
def add_film():
    data = request.json
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "Title is required"}), 400

    # validate numeric rating and year
    try:
        rating = float(data.get("rating", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid rating"}), 400
    if rating < 0:
        return jsonify({"error": "Rating cannot be negative"}), 400

    year = data.get("year")
    if year is not None:
        try:
            year = int(year)
            if year < 0:
                return jsonify({"error": "Year cannot be negative"}), 400
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid year"}), 400

    conn = get_db()
    # ensure year is not less than the earliest film year in DB (if exists)
    if year is not None:
        earliest = conn.execute("SELECT MIN(CAST(year AS INTEGER)) as min_year FROM films WHERE year IS NOT NULL").fetchone()
        if earliest and earliest["min_year"] is not None:
            try:
                min_year = int(earliest["min_year"])
                if year < min_year:
                    conn.close()
                    return jsonify({"error": f"Year cannot be earlier than {min_year}"}), 400
            except Exception:
                pass

    conn.execute("""INSERT INTO films (title, year, description, rating, poster_url)
                    VALUES (?, ?, ?, ?, ?)""",
                 (title, year, data.get("description"), rating, data.get("poster_url", "")))
    conn.commit()
    conn.close()
    return jsonify({"message": "Film přidán"})

@app.route("/admin/films/<int:film_id>", methods=["DELETE"])
def delete_film(film_id):
    conn = get_db()
    conn.execute("DELETE FROM films WHERE id=?", (film_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Film smazán"})

# ─── MOOD MATCHER (jednoduchý TF-IDF bez AI) ──────────────────────────────────

@app.route("/mood-match", methods=["POST"])
def mood_match():
    data  = request.json
    mood  = data.get("mood", "").lower()
    words = mood.split()

    conn = get_db()
    films = conn.execute("SELECT * FROM films").fetchall()
    
    results = []
    for film in films:
        desc  = (film["description"] or "").lower()
        title = (film["title"] or "").lower()
        score = sum(1 for w in words if w in desc or w in title)
        if score > 0:
            results.append((score, dict(film)))
    
    results.sort(key=lambda x: x[0], reverse=True)
    top5 = [r[1] for r in results[:5]]
    conn.close()
    return jsonify(top5)

# ─── STATS ────────────────────────────────────────────────────────────────────

@app.route("/stats", methods=["GET"])
def stats():
    conn = get_db()
    total   = conn.execute("SELECT COUNT(*) as c FROM films").fetchone()["c"]
    by_year = conn.execute("SELECT year, COUNT(*) as count FROM films GROUP BY year ORDER BY year DESC").fetchall()
    by_genre= conn.execute("""
        SELECT g.name, COUNT(*) as count FROM genres g
        JOIN film_genres fg ON g.id = fg.genre_id
        GROUP BY g.name ORDER BY count DESC LIMIT 10
    """).fetchall()
    conn.close()
    return jsonify({
        "total_films": total,
        "by_year":  [dict(r) for r in by_year],
        "by_genre": [dict(r) for r in by_genre]
    })

if __name__ == "__main__":
    # In some environments (IDEs, threads, Streamlit) the signal API is not
    # available from non-main threads which causes ValueError when the
    # werkzeug reloader tries to register signal handlers. Disable the
    # reloader to avoid this problem. If that still fails, fallback to
    # non-debug mode.
    try:
        app.run(host="0.0.0.0", port=5002, debug=True, use_reloader=False)
    except ValueError:
        # fallback without debug/reloader
        app.run(host="0.0.0.0", port=5002, debug=False)
