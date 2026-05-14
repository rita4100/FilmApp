"""Endpoints pro práci s filmy - seznam, top10, detaily, soundtrack."""
from fastapi import APIRouter, HTTPException
from ..database import get_db  # Databázové dotazy
from ..validators import normalize_search_q, parse_rating  # Validace dat
from ..external_api import get_credits, enrich_soundtracks_with_musicbrainz  # Externí API
from ..config import PER_PAGE  # Počet filmů na stránku

router = APIRouter(prefix="/films", tags=["films"])  # Všechny routes začínají /films


@router.get("")
def get_films(genre: str = None, year: int = None, rating: int = None, min_rating: int = 0, sort: str = "rating", page: int = 1, q: str = None):
    """Vrací seznam filmů s filtrováním, řazením a stránkováním."""
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
    query += f" LIMIT {PER_PAGE} OFFSET {(page-1)*PER_PAGE}"

    conn = get_db()
    films = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(f) for f in films]


@router.get("/random")
def random_film():
    """Vrací náhodně vybraný film z databáze."""
    conn = get_db()
    film = conn.execute("SELECT id, title, year, description, rating, poster_url, trailer_key FROM films ORDER BY RANDOM() LIMIT 1").fetchone()
    conn.close()
    if not film:
        raise HTTPException(status_code=404, detail="No films")
    return dict(film)


@router.get("/top10")
def top10(genre: str = None, year: int = None):
    """Vrací Top 10 filmů podle hodnocení, volitelně filtrováno žánrem a rokem."""
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


@router.get("/filter")
def filter_films(min_rating: int):
    """Jednoduchý filtr filmů podle minimálního hodnocení."""
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


@router.get("/{film_id}")
def get_film(film_id: int):
    """Vrací detailní informace o jednom filmu, včetně žánrů, soundtracků, castu a komunitních recenzí."""
    conn = get_db()
    film = conn.execute("SELECT * FROM films WHERE id = ?", (film_id,)).fetchone()
    if not film:
        conn.close()
        raise HTTPException(status_code=404, detail="Film nenalezen")

    genres = conn.execute(
        """SELECT g.name FROM genres g
           JOIN film_genres fg ON g.id = fg.genre_id
           WHERE fg.film_id = ?""",
        (film_id,)
    ).fetchall()

    soundtracks = conn.execute("SELECT song_title, artist FROM soundtracks WHERE film_id = ?", (film_id,)).fetchall()
    rating_stats = conn.execute("SELECT AVG(score) AS avg_score, COUNT(*) AS review_count FROM ratings WHERE film_id = ?", (film_id,)).fetchone()
    recent_reviews = conn.execute(
        """SELECT r.score, r.comment, r.created_at, r.updated_at, r.user_id, u.username
           FROM ratings r
           JOIN users u ON u.id = r.user_id
           WHERE r.film_id = ?
           ORDER BY r.updated_at DESC
           LIMIT 10""",
        (film_id,)
    ).fetchall()

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


@router.get("/{film_id}/soundtrack")
def get_soundtrack(film_id: int):
    """Vrací soundtrack filmu."""
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
