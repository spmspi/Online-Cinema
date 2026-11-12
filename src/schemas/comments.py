from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, field_validator


class CommentRequestSchema(BaseModel):
    text: str

    model_config = ConfigDict(from_attributes=True)


class CommentResponseSchema(CommentRequestSchema):
    id: int
    movie_id: int
    user_id: int
    created_at: datetime
    likes_count: int
    dislikes_count: int


    @field_validator("created_at")
    def read_created_at(cls, value: datetime) -> str:
        return value.strftime("%d.%m.%Y %H:%M")


class GetMovieCommentsResponseSchema(BaseModel):
    comments: list[CommentResponseSchema]
    prev_page: Optional[str]
    next_page: Optional[str]
    total_pages: int
    total_items: int

    model_config = ConfigDict(from_attributes=True)


class ResponseSubCommentSchema(BaseModel):
    parent_comment: CommentRequestSchema
    comments: str

    model_config = ConfigDict(from_attributes=True)


class SubCommetBaseSchema(BaseModel):
    id: int
    user_id: int
    created_at: datetime
    text: str
    likes_count: int
    dislikes_count: int
    model_config = ConfigDict(from_attributes=True)

    @field_validator("created_at")
    def read_created_at(cls, value: datetime) -> str:
        return value.strftime("%d.%m.%Y %H:%M")


class GetSubCommentsResponseSchema(BaseModel):
    parent_comment: CommentResponseSchema
    comments: List[SubCommetBaseSchema]
    prev_page: Optional[str]
    next_page: Optional[str]
    total_pages: int
    total_items: int

    model_config = ConfigDict(from_attributes=True)




class CommentLikeRequestSchema(BaseModel):
    is_like: bool


class CommentLikeResponseSchema(BaseModel):
    comment_id: int
    like: int
    dislike: int

