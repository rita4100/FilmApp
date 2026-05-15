"""Funkce pro komunikaci s vnějšími API (TMDB, MusicBrainz)."""
import requests
from .config import TMDB_API_KEY, BASE_URL, MUSICBRAINZ_BASE, MUSICBRAINZ_USER_AGENT
from .database import get_db  # Pro ukládání dat do DB


def fetch_tmdb_credits(tmdb_id: int):
    """Načte herce a filmový štáb z TMDB API v českém jazyce."""
    if not TMDB_API_KEY or TMDB_API_KEY.startswith("VLOZ"):
        print("Nebyl k dispozici platny TMDB API klic. Nelze nacist herce a stab.")
        return None  # Chybějící API klíč
    try:
        resp = requests.get(
            f"{BASE_URL}/movie/{tmdb_id}/credits",  # Endpoin pro credity
            params={"api_key": TMDB_API_KEY, "language": "cs-CZ"},
            timeout=10
        )
        if resp.status_code != 200:
            print(f"⚠️ TMDB credits request failed: {resp.status_code} {resp.text}")
            return None
        return resp.json()  # Vrátit data
    except Exception as exc:
        print(f"⚠️ Chyba při načítání TMDB credits: {exc}")
        return None  # Při chybě vrátit None


def fetch_tmdb_external_ids(tmdb_id: int):
    """Získá externí identifikátory filmu, jako je IMDb ID, pro další vyhledávání."""
    if not TMDB_API_KEY or TMDB_API_KEY.startswith("VLOZ"):
        return None
    try:
        resp = requests.get(
            f"{BASE_URL}/movie/{tmdb_id}/external_ids",
            params={"api_key": TMDB_API_KEY},
            timeout=10
        )
        if resp.status_code != 200:
            print(f"⚠️ TMDB external_ids request failed: {resp.status_code} {resp.text}")
            return None
        return resp.json()
    except Exception as exc:
        print(f"⚠️ Chyba při načítání TMDB external IDs: {exc}")
        return None


def fetch_tmdb_movie_details(tmdb_id: int):
    """Stáhne základní detaily o filmu v angličtině z TMDB API."""
    if not TMDB_API_KEY or TMDB_API_KEY.startswith("VLOZ"):
        return None
    try:
        resp = requests.get(
            f"{BASE_URL}/movie/{tmdb_id}",
            params={"api_key": TMDB_API_KEY, "language": "en-US"},
            timeout=10
        )
        if resp.status_code != 200:
            print(f"⚠️ TMDB movie details request failed: {resp.status_code} {resp.text}")
            return None
        return resp.json()
    except Exception as exc:
        print(f"⚠️ Chyba při načítání TMDB movie details: {exc}")
        return None


def musicbrainz_get(path: str, params: dict):
    """Provede obecný HTTP požadavek na MusicBrainz API s povinnou hlavičkou."""
    try:
        resp = requests.get(
            f"{MUSICBRAINZ_BASE}/{path}",
            params=params,
            headers={"User-Agent": MUSICBRAINZ_USER_AGENT},  # Povinný User-Agent
            timeout=10
        )
        if resp.status_code != 200:
            print(f"⚠️ MusicBrainz request failed: {resp.status_code} {resp.text}")
            return None
        return resp.json()  # Vrátit odpověď
    except Exception as exc:
        print(f"⚠️ Chyba při načítání MusicBrainz: {exc}")
        return None  # Při chybě vrátit None


def search_musicbrainz_release(imdb_id: str = None, title: str = None, year: int = None):
    """Vyhledá konkrétní soundtrackové album na MusicBrainz podle IMDb ID nebo názvu."""
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
    """Stáhne a zformátuje seznam skladeb a jejich interpretů z hudebního alba."""
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
    """Dohledá soundtrack pomocí různých kombinací údajů a uloží skladby do databáze."""
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
        conn.execute(
            "INSERT INTO soundtracks (film_id, song_title, artist) VALUES (?, ?, ?)",
            (film_id, track["song_title"], track["artist"])
        )
    conn.commit()
    conn.close()
    return tracks


def save_credits(film_id: int, credits: dict):
    """Uloží seznam herců a členů štábu do lokální databáze."""
    if not credits:
        return
    conn = get_db()
    conn.execute("DELETE FROM credits WHERE film_id = ?", (film_id,))
    for cast_member in credits.get("cast", []):
        conn.execute(
            """INSERT INTO credits (film_id, role_type, person_name, character, job, department, credit_order)
               VALUES (?, 'cast', ?, ?, ?, ?, ?)""",
            (film_id, cast_member.get("name"), cast_member.get("character"), None,
             cast_member.get("known_for_department"), cast_member.get("order", 0))
        )
    for crew_member in credits.get("crew", []):
        conn.execute(
            """INSERT INTO credits (film_id, role_type, person_name, character, job, department, credit_order)
               VALUES (?, 'crew', ?, ?, ?, ?, ?)""",
            (film_id, crew_member.get("name"), None, crew_member.get("job"),
             crew_member.get("department"), crew_member.get("order", 0))
        )
    conn.commit()
    conn.close()


def get_credits(film_id: int, tmdb_id: int = None):
    """Načte tvůrce z databáze, a pokud chybí, stáhne je z TMDB a nacachuje."""
    conn = get_db()
    rows = conn.execute(
        """SELECT role_type, person_name, character, job, department, credit_order
           FROM credits
           WHERE film_id = ?
           ORDER BY role_type, credit_order""",
        (film_id,)
    ).fetchall()
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