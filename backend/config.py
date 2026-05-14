"""Konfigurace aplikace: cesty, API klice, konstanty."""
import os
from dotenv import load_dotenv
from .seed import TMDB_API_KEY as SEED_TMDB_API_KEY

load_dotenv()  # Načíst proměnné z .env souboru

# API klice - TMDB pro metadata filmu, fallback na výchozí klíč
TMDB_API_KEY = os.environ.get("TMDB_API_KEY") or SEED_TMDB_API_KEY
if not os.environ.get("TMDB_API_KEY"):
    print("TMDB_API_KEY nebyl nalezen v prostredi. Pouzivam zalohovaci klic ze seed.py.")

BASE_URL = "https://api.themoviedb.org/3"  # API endpoint TMDB
MUSICBRAINZ_BASE = "https://musicbrainz.org/ws/2"  # API endpoint MusicBrainz pro soundtracky
MUSICBRAINZ_USER_AGENT = os.environ.get("MUSICBRAINZ_USER_AGENT", "MovieMind/1.0.0 (info@moviemind.local)")

# Cesty - adresáře pro databázi a frontend soubory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
DB_PATH = os.path.join(BASE_DIR, "films.db")  # SQLite databáze
FRONTEND_DIR = os.path.join(PROJECT_DIR, "frontend")  # Frontend statické soubory

# Konstanty - limity a stránkování
SEARCH_MAX_LEN = 200  # Maximální délka vyhledávacího dotazu
PER_PAGE = 20  # Počet filmů na stránku
