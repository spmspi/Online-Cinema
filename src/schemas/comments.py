from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, field_validator


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


class SubCommetBaseSchema(BaseModel):
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
    comments: List[SubCommetBaseSchema]
