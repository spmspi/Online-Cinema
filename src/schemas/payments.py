from typing import List

from pydantic import BaseModel, ConfigDict, field_validator

from src.database.models.accounts import UserModel


class PaymentsSchema(BaseModel):
    id: int
    user_id: int
    status: str
    amount: float
    external_payment_id: str

    model_config = ConfigDict(from_attributes=True)


class PaymentListsSchema(BaseModel):
    payments: List[PaymentsSchema]
