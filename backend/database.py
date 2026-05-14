"""Funkce pro práci s databází."""
import sqlite3
from .config import DB_PATH  # Cesta k SQLite souboru
from .db import init_db  # Inicializace schématu
from .seed import seed as seed_db  # Naplnění výchozích dat


def get_db():
    """Připojení k SQLite databázi - vrátí objekt s řádky jako dict."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Umožní přístup k sloupcům jako k atributům
    return conn


def has_films():
    """Kontrola, zda databáze obsahuje filmy - vrátí True/False."""
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM films").fetchone()[0]
    conn.close()
    return count > 0


async def seed_database_if_empty():
    """Při startu aplikace - pokud je DB prázdná, naplní ji výchozími filmy."""
    if not has_films():
        print("ℹ️ Databáze je prázdná, naplňuji filmy...")
        try:
            seed_db()  # Spustit seed skript
        except Exception as e:
            print("⚠️ Nepodařilo se naplnit databázi:", e)


# Inicializace DB při importu - vytvoří tabulky, pokud neexistují
init_db()
