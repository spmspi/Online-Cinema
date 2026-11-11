import decimal
from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, field_validator

from src.schemas.movies import MovieListSchema


class OrderSchema(BaseModel):
    id: int
    user_id: int
    created_at: datetime
    status: str
    total_amount: decimal.Decimal

    model_config = ConfigDict(from_attributes=True)

    @field_validator("created_at")
    def read_created_at(cls, value: datetime) -> str:
        return value.strftime("%d.%m.%Y %H:%M")


class OrderListSchema(BaseModel):
    user_id: int
    orders: List[OrderSchema]

    model_config = ConfigDict(from_attributes=True)

class OrderDetailSchema(BaseModel):
    id: int
    user_id: int
    created_at: datetime
    movies: List[MovieListSchema]

    model_config = ConfigDict(from_attributes=True)

    @field_validator("created_at")
    def read_created_at(cls, value: datetime) -> str:
        return value.strftime("%d.%m.%Y %H:%M")