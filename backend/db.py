import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "films.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 1. Filmy (ponecháno, přidáno tmdb_id pro ty automatické aktualizace)
    # Upravená tabulka films se dvěma zdroji hodnocení
    c.execute("""CREATE TABLE IF NOT EXISTS films (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tmdb_id INTEGER UNIQUE,
        title TEXT,
        year INTEGER,
        description TEXT,
        rating_tmdb REAL,    -- Globální hodnocení (TMDb)
        rating_czdb REAL,    -- České hodnocení (CZDB)
        poster_url TEXT,
        trailer_key TEXT
    )""")

    # 2. Žánry a spojovací tabulka
    c.execute("""CREATE TABLE IF NOT EXISTS genres (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS film_genres (
        film_id INTEGER,
        genre_id INTEGER,
        PRIMARY KEY (film_id, genre_id),
        FOREIGN KEY(film_id) REFERENCES films(id),
        FOREIGN KEY(genre_id) REFERENCES genres(id)
    )""")

    # 3. Uživatelé
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT DEFAULT 'user',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    # 4. Historie banů
    c.execute("""CREATE TABLE IF NOT EXISTS user_bans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        banned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        reason TEXT,
        is_active INTEGER DEFAULT 1,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")

    # 5. Hodnocení
    c.execute("""CREATE TABLE IF NOT EXISTS ratings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        film_id INTEGER,
        score INTEGER,
        comment TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, film_id),
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(film_id) REFERENCES films(id)
    )""")

    # 6. Watchlist (přidán čas přidání)
    c.execute("""CREATE TABLE IF NOT EXISTS watchlist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        film_id INTEGER,
        status TEXT, -- např. 'seen', 'want'
        added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, film_id),
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(film_id) REFERENCES films(id)
    )""")

    # 7. Soundtracky
    c.execute("""CREATE TABLE IF NOT EXISTS soundtracks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        film_id INTEGER,
        song_title TEXT,
        artist TEXT,
        FOREIGN KEY(film_id) REFERENCES films(id)
    )""")

    # Default admin (všimni si, že 'banned' už v tabulce users není)
    c.execute("""INSERT OR IGNORE INTO users (username, password, role) 
                 VALUES ('admin', 'admin123', 'admin')""")

    conn.commit()
    conn.close()
    print("✅ Databáze byla úspěšně aktualizována s časovými značkami a historií banů!")

if __name__ == "__main__":
    # POZOR: Pokud chceš změny aplikovat na existující db, 
    # nejprve starý soubor films.db smaž, aby se tabulky vytvořily znovu.
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("🗑️ Stará databáze smazána pro čistou re-instalaci.")
    init_db()
    