from pydantic import BaseModel


class FavoriteCreate(BaseModel):
    album_id: str
    album_name: str
    artist_name: str
    cover_art_url: str


class Favorite(FavoriteCreate):
    id: int

    class Config:
        from_attributes = True
