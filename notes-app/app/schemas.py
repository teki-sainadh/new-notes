from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# ── Auth ──────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

    model_config = {
        "json_schema_extra": {
            "example": {"email": "user@example.com", "password": "mypassword123"}
        }
    }


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str


# ── Notes ─────────────────────────────────────────────
class NoteCreate(BaseModel):
    title: str
    content: str

    model_config = {
        "json_schema_extra": {
            "example": {"title": "My first note", "content": "Hello world!"}
        }
    }


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None


class NoteResponse(BaseModel):
    id: str
    title: str
    content: str
    is_pinned: bool
    created_at: datetime
    updated_at: datetime


class ShareRequest(BaseModel):
    share_with_email: EmailStr


# ── Pagination ────────────────────────────────────────
class PaginatedNotes(BaseModel):
    total: int
    page: int
    per_page: int
    notes: list[NoteResponse]
