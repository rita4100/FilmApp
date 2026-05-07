import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "films.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS films (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tmdb_id INTEGER UNIQUE,
        title TEXT,
        year INTEGER,
        description TEXT,
        rating REAL,
        poster_url TEXT,
        trailer_key TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS genres (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS film_genres (
        film_id INTEGER,
        genre_id INTEGER,
        PRIMARY KEY (film_id, genre_id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS soundtracks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        film_id INTEGER,
        song_title TEXT,
        artist TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT DEFAULT 'user',
        banned INTEGER DEFAULT 0
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS watchlist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        film_id INTEGER,
        status TEXT,
        UNIQUE(user_id, film_id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS ratings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        film_id INTEGER,
        score INTEGER,
        UNIQUE(user_id, film_id)
    )""")

    # Default admin user (password: admin123)
    c.execute("""INSERT OR IGNORE INTO users (username, password, role) 
                 VALUES ('admin', 'admin123', 'admin')""")

    conn.commit()
    conn.close()
    print("✅ Databáze vytvořena!")

if __name__ == "__main__":
    init_db()
