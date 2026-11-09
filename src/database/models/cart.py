from datetime import datetime, date, timedelta, timezone

from sqlalchemy import Integer, ForeignKey, UniqueConstraint, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.movies import MovieModel
from src.database.models.accounts import UserModel
from src.database.models.base import Base


class CartModel(Base):
    __tablename__ = 'cart'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True)
    user: Mapped[UserModel] = relationship("UserModel", back_populates="cart")

    cart_items: Mapped[list["CartItem"]] = relationship(
        "CartItem",
        back_populates="cart",
        cascade="all, delete-orphan",
    )

    __table_args__ = (UniqueConstraint("user_id"),)


class CartItemModel(Base):
    __tablename__ = 'cart_item'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("cart.id", ondelete="CASCADE"),)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"),)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    cart: Mapped["Cart"] = relationship("Cart", back_populates="cart_item")
    movie: Mapped["MovieModel"] = relationship("MovieModel")

    __table_args__ = (UniqueConstraint("movie_id", "cart_id"),)
