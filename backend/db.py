import sqlite3
import os

# Definice cest k souborům
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "films.db")

def init_db():
    """
    Inicializuje SQLite databázi se strukturou odpovídající požadavkům na:
    - Oddělení uživatelských dat a historie banů
    - Dvojitý externí rating (TMDb a CZDB)
    - Časové stopy (timestamps) u všech akcí
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Povolení podpory cizích klíčů v SQLite
    c.execute("PRAGMA foreign_keys = ON;")

    # 1. TABULKA: Filmy (Katalog s externími daty)
    c.execute("""CREATE TABLE IF NOT EXISTS films (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tmdb_id INTEGER UNIQUE,         -- Unikátní ID pro synchronizaci s TMDb
        title TEXT NOT NULL,
        year INTEGER,
        description TEXT,
        rating_tmdb REAL,               -- Globální hodnocení z TMDb API
        rating_czdb REAL,               -- České hodnocení z CZDB API
        poster_url TEXT,
        trailer_key TEXT                -- ID pro YouTube trailer
    )""")

    # 2. TABULKA: Žánry (Číselník)
    c.execute("""CREATE TABLE IF NOT EXISTS genres (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )""")

    # 3. TABULKA: Propojení Filmů a Žánrů (Vztah M:N)
    c.execute("""CREATE TABLE IF NOT EXISTS film_genres (
        film_id INTEGER,
        genre_id INTEGER,
        PRIMARY KEY (film_id, genre_id),
        FOREIGN KEY(film_id) REFERENCES films(id) ON DELETE CASCADE,
        FOREIGN KEY(genre_id) REFERENCES genres(id) ON DELETE CASCADE
    )""")

    # 4. TABULKA: Uživatelé (Čistá tabulka bez historie banů)
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'user',        -- Role: 'user' nebo 'admin'
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    # 5. TABULKA: Historie banů (Odděleno pro sledování času a důvodu)
    c.execute("""CREATE TABLE IF NOT EXISTS user_bans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        banned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        reason TEXT,
        is_active INTEGER DEFAULT 1,    -- 1 = aktivní ban, 0 = zrušený
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")

    # 6. TABULKA: Uživatelská hodnocení (Vlastní komunitní data)
    c.execute("""CREATE TABLE IF NOT EXISTS ratings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        film_id INTEGER,
        score INTEGER CHECK(score >= 1 AND score <= 10), -- Naše vlastní škála 1-10
        comment TEXT,                    -- Slovní poznámka uživatele
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, film_id),        -- Každý uživatel hodnotí jeden film jen jednou
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(film_id) REFERENCES films(id) ON DELETE CASCADE
    )""")

    # 7. TABULKA: Watchlist (Plánované a viděné filmy)
    c.execute("""CREATE TABLE IF NOT EXISTS watchlist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        film_id INTEGER,
        status TEXT DEFAULT 'want',     -- 'want' (chci vidět), 'seen' (viděl jsem)
        added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, film_id),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(film_id) REFERENCES films(id) ON DELETE CASCADE
    )""")

    # 8. TABULKA: Soundtracky (Inspirace z filmu)
    c.execute("""CREATE TABLE IF NOT EXISTS soundtracks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        film_id INTEGER,
        song_title TEXT,
        artist TEXT,
        FOREIGN KEY(film_id) REFERENCES films(id) ON DELETE CASCADE
    )""")

    # Vytvoření výchozího administrátora
    c.execute("""INSERT OR IGNORE INTO users (username, password, role) 
                 VALUES ('admin', 'admin123', 'admin')""")

    conn.commit()
    conn.close()
    print("✅ Databáze MovieMind inicializována.")

if __name__ == "__main__":
    # Pokud měníme strukturu tabulek, je nejlepší starou DB smazat (pro vývoj)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("🗑️ Stará databáze smazána.")
    
    init_db()