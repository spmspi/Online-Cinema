from datetime import datetime, date, timedelta, timezone
import enum
from typing import Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DECIMAL,
    ForeignKey,
    Table,
    CheckConstraint,
    UniqueConstraint,
    Boolean,
    Enum,
    DateTime,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.order import OrdersModel
from src.database.models.movies import MovieModel
from src.database.models.accounts import UserModel
from src.database.models.base import Base



class StatusPaymentsEnum(str, enum.Enum):
    SUCCESSFUL = "successful"
    CANCELED = "canceled"
    REFUNDED = "refunded"


class PaymentsModel(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    status: Mapped[Optional[StatusPaymentsEnum]] = mapped_column(Enum(StatusPaymentsEnum))
    amount: Mapped[float] = mapped_column(DECIMAL(10, 2))
    external_payment_id: Mapped[str] = mapped_column(String)

    user: Mapped[UserModel] = relationship("UserModel", back_populates="payments")
    order: Mapped[OrdersModel] = relationship("OrdersModel", back_populates="payments")
    order_items: Mapped[list["PaymentsItemModel"]] = relationship(
        "PaymentsItemModel",
        back_populates="payment",
        cascade="all, delete-orphan",
    )


class PaymentsItemModel(Base):
    __tablename__ = "payments_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id", ondelete="CASCADE"))
    order_item_id: Mapped[int] = mapped_column(ForeignKey("order_items.id", ondelete="CASCADE"))
    price_at_payment: Mapped[float] = mapped_column(DECIMAL(10, 2))


    payment: Mapped[PaymentsModel] = relationship("PaymentsModel", back_populates="order_items")

    __table_args__ = (UniqueConstraint("payment_id", "order_item_id"),)
