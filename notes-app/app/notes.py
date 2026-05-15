from fastapi import APIRouter, HTTPException, status, Depends, Query
from app.schemas import NoteCreate, NoteUpdate, NoteResponse, ShareRequest, PaginatedNotes
from app.auth import get_current_user
from app.database import supabase
from datetime import datetime, timezone

router = APIRouter(prefix="/notes", tags=["Notes"])


def _now():
    return datetime.now(timezone.utc).isoformat()


def _get_note_or_403(note_id: str, user_id: str):
    """Fetch note by id. Allows owner OR someone the note was shared with."""
    # Check owner
    result = supabase.table("notes").select("*").eq("id", note_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Note not found")

    note = result.data[0]

    # Owner check
    if note["owner_id"] == user_id:
        return note

    # Shared check
    shared = (
        supabase.table("shared_notes")
        .select("id")
        .eq("note_id", note_id)
        .eq("shared_with_user_id", user_id)
        .execute()
    )
    if shared.data:
        return note

    raise HTTPException(status_code=403, detail="Access denied")


# ── GET /notes ───────────────────────────────────────
@router.get("", status_code=200)
def get_all_notes(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["sub"]

    # Notes owned by user
    owned = supabase.table("notes").select("*").eq("owner_id", user_id).execute()
    owned_ids = {n["id"] for n in owned.data}

    # Notes shared with user
    shared_links = supabase.table("shared_notes").select("note_id").eq("shared_with_user_id", user_id).execute()
    shared_ids = [r["note_id"] for r in shared_links.data if r["note_id"] not in owned_ids]

    all_notes = list(owned.data)
    if shared_ids:
        shared_notes = supabase.table("notes").select("*").in_("id", shared_ids).execute()
        all_notes.extend(shared_notes.data)

    # Sort: pinned first, then by updated_at desc
    all_notes.sort(key=lambda n: (not n.get("is_pinned", False), n["updated_at"]), reverse=False)
    all_notes.sort(key=lambda n: n.get("is_pinned", False), reverse=True)

    total = len(all_notes)
    start = (page - 1) * per_page
    paginated = all_notes[start: start + per_page]

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "notes": paginated
    }


# ── GET /notes/{id} ──────────────────────────────────
@router.get("/{note_id}", status_code=200)
def get_note(note_id: str, current_user: dict = Depends(get_current_user)):
    return _get_note_or_403(note_id, current_user["sub"])


# ── POST /notes ──────────────────────────────────────
@router.post("", status_code=201)
def create_note(body: NoteCreate, current_user: dict = Depends(get_current_user)):
    if not body.title.strip():
        raise HTTPException(status_code=422, detail="Title cannot be empty")
    if not body.content.strip():
        raise HTTPException(status_code=422, detail="Content cannot be empty")

    now = _now()
    result = supabase.table("notes").insert({
        "title": body.title.strip(),
        "content": body.content.strip(),
        "owner_id": current_user["sub"],
        "is_pinned": False,
        "created_at": now,
        "updated_at": now
    }).execute()

    return result.data[0]


# ── PUT /notes/{id} ──────────────────────────────────
@router.put("/{note_id}", status_code=200)
def update_note(note_id: str, body: NoteUpdate, current_user: dict = Depends(get_current_user)):
    note = _get_note_or_403(note_id, current_user["sub"])

    # Only owner can edit
    if note["owner_id"] != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Only the owner can edit this note")

    updates = {"updated_at": _now()}
    if body.title is not None:
        if not body.title.strip():
            raise HTTPException(status_code=422, detail="Title cannot be empty")
        updates["title"] = body.title.strip()
    if body.content is not None:
        if not body.content.strip():
            raise HTTPException(status_code=422, detail="Content cannot be empty")
        updates["content"] = body.content.strip()

    result = supabase.table("notes").update(updates).eq("id", note_id).execute()
    return result.data[0]


# ── DELETE /notes/{id} ───────────────────────────────
@router.delete("/{note_id}", status_code=204)
def delete_note(note_id: str, current_user: dict = Depends(get_current_user)):
    note = _get_note_or_403(note_id, current_user["sub"])

    if note["owner_id"] != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Only the owner can delete this note")

    # Also delete all share records for this note
    supabase.table("shared_notes").delete().eq("note_id", note_id).execute()
    supabase.table("notes").delete().eq("id", note_id).execute()
    return None


# ── POST /notes/{id}/share ───────────────────────────
@router.post("/{note_id}/share", status_code=200)
def share_note(note_id: str, body: ShareRequest, current_user: dict = Depends(get_current_user)):
    note = _get_note_or_403(note_id, current_user["sub"])

    if note["owner_id"] != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Only the owner can share this note")

    # Find user to share with
    target = supabase.table("users").select("id, email").eq("email", body.share_with_email).execute()
    if not target.data:
        raise HTTPException(status_code=404, detail="User with that email not found")

    target_user = target.data[0]

    if target_user["id"] == current_user["sub"]:
        raise HTTPException(status_code=400, detail="You cannot share a note with yourself")

    # Check if already shared
    already = (
        supabase.table("shared_notes")
        .select("id")
        .eq("note_id", note_id)
        .eq("shared_with_user_id", target_user["id"])
        .execute()
    )
    if already.data:
        return {"message": f"Note already shared with {body.share_with_email}"}

    supabase.table("shared_notes").insert({
        "note_id": note_id,
        "shared_with_user_id": target_user["id"],
        "shared_at": _now()
    }).execute()

    return {"message": f"Note successfully shared with {body.share_with_email}"}


# ── POST /notes/{id}/pin  (Custom Feature 💡) ────────
@router.post("/{note_id}/pin", status_code=200)
def toggle_pin(note_id: str, current_user: dict = Depends(get_current_user)):
    """
    Custom Feature: Pin / Unpin a note.
    Pinned notes always appear at the top of GET /notes.
    Only the owner can pin/unpin.
    """
    note = _get_note_or_403(note_id, current_user["sub"])

    if note["owner_id"] != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Only the owner can pin this note")

    new_pin_state = not note.get("is_pinned", False)
    result = supabase.table("notes").update({
        "is_pinned": new_pin_state,
        "updated_at": _now()
    }).eq("id", note_id).execute()

    action = "pinned" if new_pin_state else "unpinned"
    return {"message": f"Note {action} successfully", "is_pinned": new_pin_state}
