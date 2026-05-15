from fastapi import APIRouter, Query, Depends
from app.auth import get_current_user
from app.database import supabase

router = APIRouter(tags=["Search"])


@router.get("/search", status_code=200)
def search_notes(
    q: str = Query(..., min_length=1, description="Search keyword"),
    current_user: dict = Depends(get_current_user)
):
    """Search notes by keyword in title or content (stretch goal)."""
    user_id = current_user["sub"]
    keyword = q.lower().strip()

    # Get all notes accessible to user (owned + shared)
    owned = supabase.table("notes").select("*").eq("owner_id", user_id).execute()
    owned_ids = {n["id"] for n in owned.data}

    shared_links = supabase.table("shared_notes").select("note_id").eq("shared_with_user_id", user_id).execute()
    shared_ids = [r["note_id"] for r in shared_links.data if r["note_id"] not in owned_ids]

    all_notes = list(owned.data)
    if shared_ids:
        shared_notes = supabase.table("notes").select("*").in_("id", shared_ids).execute()
        all_notes.extend(shared_notes.data)

    # Filter by keyword in title or content
    results = [
        n for n in all_notes
        if keyword in n["title"].lower() or keyword in n["content"].lower()
    ]

    return {"query": q, "results": results, "count": len(results)}
