"""Authentication router."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import User
from app.schemas import LoginRequest, PasswordChangeRequest, SetupRequest
from app.security import create_password, verify_password

router = APIRouter()


# -------------------------------------------------------------------- #
# POST /setup – first-time password setup
# -------------------------------------------------------------------- #
@router.post("/setup")
async def setup(
    request: SetupRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Create or reset the single local user credentials."""
    existing = db.query(User).first()
    salt_hash = create_password(request.password)

    if existing:
        existing.username = request.username
        existing.password_hash = salt_hash["password_hash"]
        existing.salt = salt_hash["salt"]
        db.commit()
        return {"message": "Credentials updated successfully"}

    user = User(
        username=request.username,
        password_hash=salt_hash["password_hash"],
        salt=salt_hash["salt"],
    )
    db.add(user)
    db.commit()
    return {"message": "Password set successfully"}


# -------------------------------------------------------------------- #
# POST /login – verify password
# -------------------------------------------------------------------- #
@router.post("/login")
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Authenticate with username and password."""
    user = db.query(User).filter(User.username == request.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not verify_password(request.password, user.password_hash, user.salt):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    return {"message": "Login successful"}


# -------------------------------------------------------------------- #
# POST /change-password – update password
# -------------------------------------------------------------------- #
@router.post("/change-password")
async def change_password(
    request: PasswordChangeRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Verify old password and set a new one."""
    user = db.query(User).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No user found.",
        )

    if not verify_password(request.old_password, user.password_hash, user.salt):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Old password is incorrect",
        )

    new_salt_hash = create_password(request.new_password)
    user.password_hash = new_salt_hash["password_hash"]
    user.salt = new_salt_hash["salt"]
    db.commit()
    return {"message": "Password changed successfully"}


# -------------------------------------------------------------------- #
# GET /has-user – check if user exists
# -------------------------------------------------------------------- #
@router.get("/has-user")
async def has_user(db: Session = Depends(get_db)) -> dict:
    """Return whether at least one user record exists."""
    user = db.query(User).first()
    return {"has_user": user is not None}
