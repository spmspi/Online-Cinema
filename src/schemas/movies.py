from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from src.database.models.movies import MovieModel

class MovieListItemSchema(BaseModel):
    id: int
    name: str
    date: date
    score: float
    description: str

    model_config = ConfigDict(from_attributes=True)


class MovieListResponseSchema(BaseModel):
    movies: List[MovieListItemSchema]
    prev_page: Optional[str]
    next_page: Optional[str]
    total_pages: int
    total_items: int

    model_config = ConfigDict(from_attributes=True)
