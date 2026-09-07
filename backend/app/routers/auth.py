"""
/auth endpoints — signup and login.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.db_models import User
from app.models.schemas import UserSignup, UserLogin, TokenResponse
from app.auth import hash_password, verify_password, create_access_token

router = APIRouter()


@router.post("/signup", response_model=TokenResponse)
def signup(data: UserSignup, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    new_user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        display_name=data.display_name,
        role="citizen",
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token(new_user.id, new_user.email)
    return TokenResponse(access_token=token, user_id=new_user.id, email=new_user.email)


@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    token = create_access_token(user.id, user.email)
    return TokenResponse(access_token=token, user_id=user.id, email=user.email)
