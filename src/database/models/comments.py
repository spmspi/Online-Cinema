from datetime import datetime

from sqlalchemy import Integer, ForeignKey, Text, DateTime, func
from sqlalchemy.orm import mapped_column, Mapped, relationship
from .base import Base


class CommentModel(Base):
    __tablename__ = "movies_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    movie_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("movies.id", ondelete="CASCADE"), nullable=False
    )

    sub_comments: Mapped[list["SubCommentModel"]] = relationship(
        "SubCommentModel", back_populates="comment", cascade="all, delete-orphan"
    )
    user = relationship("UserModel")
    movie: Mapped["MovieModel"] = relationship("MovieModel", back_populates="comments")

    @classmethod
    def default_order_by(cls):
        return [cls.created_at.asc()]


class SubCommentModel(Base):
    __tablename__ = "movies_sub_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    comment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("movies_comments.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    comment: Mapped["CommentModel"] = relationship(
        "CommentModel", back_populates="sub_comments"
    )
    user = relationship("UserModel")

    @classmethod
    def default_order_by(cls):
        return [cls.created_at.asc()]
