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

from src.database.models.movies import MovieModel
from src.database.models.accounts import UserModel
from src.database.models.base import Base

class StatusOrderEnum(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELED = "canceled"


class OrdersModel(Base):
    __tablename__ = 'orders'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    status: Mapped[Optional[StatusOrderEnum]] = mapped_column(Enum(StatusOrderEnum), nullable=False, default=StatusOrderEnum.PENDING)
    total_amount: Mapped[float] = mapped_column(DECIMAL(10, 2))

    user: Mapped[UserModel] = relationship("UserModel", back_populates="orders")
    order_items: Mapped[list["OrderItemModel"]] = relationship(
        "OrderItemModel",
        back_populates="order",
        cascade="all, delete-orphan",
    )



class OrderItemModel(Base):
    __tablename__ = 'order_items'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    price_at_order: Mapped[float] = mapped_column(DECIMAL(10, 2))
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"),)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"),)

    order: Mapped["OrdersModel"] = relationship("OrdersModel", back_populates="order_items")
    movie: Mapped["MovieModel"] = relationship("MovieModel", back_populates="order_items")

    __table_args__ = (UniqueConstraint("movie_id", "order_id"),)
