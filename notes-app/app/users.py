from fastapi import APIRouter, HTTPException, status
from app.schemas import RegisterRequest, LoginRequest, TokenResponse
from app.auth import hash_password, verify_password, create_access_token
from app.database import supabase

router = APIRouter(tags=["Authentication"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest):
    # Check if email already exists
    existing = supabase.table("users").select("id").eq("email", body.email).execute()
    if existing.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    # Validate password strength
    if len(body.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 6 characters"
        )

    hashed = hash_password(body.password)
    supabase.table("users").insert({
        "email": body.email,
        "password_hash": hashed
    }).execute()

    return {"message": "User registered successfully"}


@router.post("/login", status_code=status.HTTP_200_OK, response_model=TokenResponse)
def login(body: LoginRequest):
    result = supabase.table("users").select("*").eq("email", body.email).execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    user = result.data[0]

    if not verify_password(body.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    token = create_access_token({"sub": user["id"], "email": user["email"]})
    return {"access_token": token}
