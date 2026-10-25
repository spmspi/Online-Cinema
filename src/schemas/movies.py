from datetime import date
from typing import List, Optional

from pydantic import BaseModel

from src.database.models.movies import MovieModel

class MovieListItemSchema(BaseModel):
    id: int
    name: str
    date: date
    score: float
    description: str


class MovieListResponseSchema(BaseModel):
    movies: List[MovieModel]
    prev_page: Optional[str]
    next_page: Optional[str]
    total_pages: int
    total_items: int