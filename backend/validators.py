"""Funkce pro validaci a normalizaci dat."""
from fastapi import HTTPException


def normalize_search_q(q: str | None) -> str | None:
    """Normalizuje vyhledávací dotaz - zkrátí, očistí, převede na malá písmena."""
    from .config import SEARCH_MAX_LEN
    
    if q is None:
        return None
    s = q.strip()  # Odebrat mezery
    if not s:
        return None
    if len(s) > SEARCH_MAX_LEN:
        s = s[:SEARCH_MAX_LEN]  # Omezit délku
    return s.lower()  # Normalizovat na malá písmena pro porovnání


def parse_rating(value, default=0):
    """Validuje a konvertuje hodnocení (0-10). Vrátí default, pokud je prázdné."""
    if value in (None, ""):
        return default  # Vrátit výchozí hodnotu
    if isinstance(value, bool):
        raise HTTPException(status_code=400, detail="Hodnocení musí být celé číslo od 0 do 10")
    try:
        score = int(value)  # Konvertovat na číslo
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Hodnocení musí být celé číslo od 0 do 10")
    if score < 0 or score > 10:  # Zkontrolovat rozsah
        raise HTTPException(status_code=400, detail="Hodnocení musí být celé číslo od 0 do 10")
    return score


def parse_user_rating(value):
    """Validuje uživatelské hodnocení - musí být 1-10, ne 0."""
    score = parse_rating(value, default=None)  # Nejdříve základní validace
    if score is None or score < 1:  # Uživatel musí vybrat alespoň 1 hvězdu
        raise HTTPException(status_code=400, detail="Hodnocení musí být celé číslo od 1 do 10")
    return score
