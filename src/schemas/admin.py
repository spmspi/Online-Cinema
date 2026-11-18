from typing import List

from pydantic import BaseModel, ConfigDict

from src.schemas.order import OrderSchema


class AdminOrderDetailSchema(BaseModel):
    total: int
    orders: List[OrderSchema]

    model_config = ConfigDict(from_attributes=True)
