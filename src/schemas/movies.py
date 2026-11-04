from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator



class MovieListItemSchema(BaseModel):
    id: int
    name: str
    year: int
    meta_score: float
    description: str

    model_config = ConfigDict(from_attributes=True)


class MovieListResponseSchema(BaseModel):
    movies: List[MovieListItemSchema]
    prev_page: Optional[str]
    next_page: Optional[str]
    total_pages: int
    total_items: int

    model_config = ConfigDict(from_attributes=True)

class CertificationSchema(BaseModel):
    name: str

    model_config = ConfigDict(from_attributes=True)

class GenresSchema(BaseModel):
    name: str

    model_config = ConfigDict(from_attributes=True)

class StarsSchema(BaseModel):
    name: str

    model_config = ConfigDict(from_attributes=True)

class DirectorsSchema(BaseModel):
    name: str

    model_config = ConfigDict(from_attributes=True)

class MovieCreateRequestSchema(BaseModel):
    name: str
    year: int
    time: int
    imdb: float
    votes: int
    meta_score: float
    gross: float
    description: str
    price: float
    certification: str
    genres: List[str]
    stars: List[str]
    directors: List[str]
    model_config = ConfigDict(from_attributes=True)

class MovieDetailResponseSchema(MovieCreateRequestSchema):
    id: int
    certification: CertificationSchema
    genres: List[GenresSchema]
    stars: List[StarsSchema]
    directors: List[DirectorsSchema]


class MovieUpdateSchema(BaseModel):
    name: Optional[str] = None
    year: Optional[int] = None
    time: Optional[int] = None
    imdb: Optional[float] = None
    votes: Optional[int] = None
    meta_score: Optional[float] = None
    gross: Optional[float] = None
    description: Optional[str] = None
    price: Optional[float] = None



class MovieRatingResponseSchema(BaseModel):
    movie_id: int
    meta_score: float


class MovieRatingRequestSchema(BaseModel):
    score: float


class MovieLikeRequestSchema(BaseModel):
    is_like: bool

class MovieLikeResponseSchema(BaseModel):
    movie_id: int
    like: int
    dislike: int



class CommentRequestSchema(BaseModel):
    text: str

    model_config = ConfigDict(from_attributes=True)

class CommentResponseSchema(CommentRequestSchema):
    id: int
    movie_id: int
    user_id: int
    created_at: datetime

    @field_validator("created_at")
    def read_created_at(cls, value: datetime) -> str:
        return value.strftime("%d.%m.%Y %H:%M")


class GetMovieCommentsResponseSchema(BaseModel):
    comments: List[CommentResponseSchema]

    model_config = ConfigDict(from_attributes=True)


class ResponseSubCommentSchema(BaseModel):
    parent_comment: CommentRequestSchema
    comments: str

    model_config = ConfigDict(from_attributes=True)


class SubCommetBaseScgema(BaseModel):
    id: int
    user_id: int
    created_at: datetime
    text: str
    model_config = ConfigDict(from_attributes=True)

    @field_validator("created_at")
    def read_created_at(cls, value: datetime) -> str:
        return value.strftime("%d.%m.%Y %H:%M")


class GetSubCommentsResponseSchema(BaseModel):
    parent_comment: CommentRequestSchema
    comments: List[SubCommetBaseScgema]