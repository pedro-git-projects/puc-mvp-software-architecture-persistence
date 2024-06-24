from datetime import timedelta
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from contextlib import asynccontextmanager

from sqlalchemy.orm import Session

from app import models
from app.auth import auth, utils, schemas
from app.database import get_db, init_db
from app.favorites.schemas import Favorite, FavoriteCreate


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Item(BaseModel):
    id: Optional[int] = None
    name: str
    description: str


@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = auth.get_user(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email já registrado")
    hashed_password = utils.get_password_hash(user.password)
    db_user = models.User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.post("/token", response_model=schemas.Token)
def login_for_access_token(
    db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me/", response_model=schemas.User)
def read_users_me(current_user: schemas.User = Depends(auth.get_current_user)):
    return current_user


@app.delete("/users/me", response_model=schemas.User)
def delete_user(
    current_user: schemas.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    user = auth.get_user(db, email=current_user.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return user


@app.put("/users/me/password", response_model=schemas.User)
def change_password(
    password_change: schemas.PasswordChange,
    current_user: schemas.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    user = auth.get_user(db, email=current_user.email)
    if not user or not utils.verify_password(
        password_change.old_password, user.hashed_password
    ):
        raise HTTPException(status_code=400, detail="Incorrect password")
    user.hashed_password = utils.get_password_hash(password_change.new_password)
    db.commit()
    db.refresh(user)
    return user


@app.post("/users/me/favorites", response_model=Favorite)
def add_favorite(
    favorite: FavoriteCreate,
    current_user: schemas.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    db_favorite = models.Favorite(
        user_id=current_user.id,
        album_id=favorite.album_id,
        album_name=favorite.album_name,
        artist_name=favorite.artist_name,
        cover_art_url=favorite.cover_art_url,
    )
    db.add(db_favorite)
    db.commit()
    db.refresh(db_favorite)
    return db_favorite


@app.get("/users/me/favorites", response_model=List[Favorite])
def get_favorites(
    current_user: schemas.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.Favorite)
        .filter(models.Favorite.user_id == current_user.id)
        .all()
    )
