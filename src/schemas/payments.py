from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, field_validator, field_serializer

from src.database.models.accounts import UserModel


class PaymentsSchema(BaseModel):
    id: int
    user_id: int
    status: str
    created_at: datetime
    amount: float
    external_payment_id: str

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at")
    def read_created_at(self, value: datetime) -> str:
        return value.strftime("%d.%m.%Y %H:%M")


class PaymentListsSchema(BaseModel):
    payments: List[PaymentsSchema]
