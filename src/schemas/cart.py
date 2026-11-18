from pydantic import BaseModel
from typing import List

from src.schemas.movies import MovieListSchema


class CartBaseSchema(BaseModel):
    pass


class CartListResponseSchema(BaseModel):
    cart_id: int
    movies: List[MovieListSchema]
