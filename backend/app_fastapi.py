"""
FastAPI backend про jednoduchou filmovou aplikaci.
Pouze endpoints - veškeré logiky jsou v modulech.
"""
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from .config import FRONTEND_DIR
from .database import seed_database_if_empty
from .routes import films, genres, users, watchlist, ratings, admin, stats, frontend

# Inicializace FastAPI aplikace
app = FastAPI(title="FilmApp API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Statické soubory
app.mount("/static", StaticFiles(directory=os.path.join(FRONTEND_DIR, "static")), name="static")

# Registrace všech routes
app.include_router(films.router)
app.include_router(genres.router)
app.include_router(users.router)
app.include_router(watchlist.router)
app.include_router(ratings.router)
app.include_router(admin.router)
app.include_router(stats.router)
app.include_router(frontend.router)

# Startup event - naplní databázi při startu, pokud je prázdná
@app.on_event("startup")
async def startup():
    await seed_database_if_empty()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app_fastapi:app", host="0.0.0.0", port=8000, reload=True)
