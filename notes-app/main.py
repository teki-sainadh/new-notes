from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.users import router as users_router
from app.notes import router as notes_router
from app.search import router as search_router

app = FastAPI(
    title="Notes App API",
    description="A multi-user notes backend — like Google Keep with REST APIs.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS — allow all origins (fine for an intern assignment / public API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────
app.include_router(users_router)
app.include_router(notes_router)
app.include_router(search_router)


# ── About ─────────────────────────────────────────────
@app.get("/about", tags=["Info"])
def about():
    return {
        "name": "Teki Sainadh",
        "email": "tekisainadh@gmail.com",
        "my features": {
            "Pin / Unpin Notes": (
                "POST /notes/{id}/pin — Toggle a note as pinned. "
                "Pinned notes always float to the top of GET /notes. "
                "I chose this because it's genuinely useful UX — "
                "users always have a few notes they need quick access to."
            ),
            "Full-Text Search": (
                "GET /search?q=keyword — Search across all notes the user can access "
                "(owned + shared) by matching the keyword in title or content."
            ),
            "Pagination": (
                "GET /notes?page=1&per_page=10 — Paginated note listing "
                "so the API stays fast even with hundreds of notes."
            )
        }
    }


# ── Health check ──────────────────────────────────────
@app.get("/", tags=["Info"])
def root():
    return {"status": "ok", "message": "Notes API is running 🚀"}
