from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, field_validator

from src.database.models.accounts import UserModel


class PaymentsSchema(BaseModel):
    id: int
    user_id: int
    status: str
    created_at: datetime
    amount: float
    external_payment_id: str

    model_config = ConfigDict(from_attributes=True)

    @field_validator("created_at")
    def read_created_at(cls, value: datetime) -> str:
        return value.strftime("%d.%m.%Y %H:%M")


class PaymentListsSchema(BaseModel):
    payments: List[PaymentsSchema]
