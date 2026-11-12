from datetime import datetime

from sqlalchemy import Integer, ForeignKey, Text, DateTime, func, Boolean, UniqueConstraint
from sqlalchemy.orm import mapped_column, Mapped, relationship
from .base import Base


class CommentModel(Base):
    __tablename__ = "movies_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    likes_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    dislikes_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

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

    likes: Mapped[list["CommentLikeModel"]] = relationship(
        "CommentLikeModel", back_populates="comment", cascade="all, delete-orphan"
    )

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
    likes_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    dislikes_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

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
    likes: Mapped[list["SubCommentLikeModel"]] = relationship(
        "SubCommentLikeModel", back_populates="sub_comment", cascade="all, delete-orphan"
    )

    @classmethod
    def default_order_by(cls):
        return [cls.created_at.asc()]


class CommentLikeModel(Base):
    __tablename__ = "comment_likes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    is_like: Mapped[bool] = mapped_column(Boolean, nullable=False)

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    comment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("movies_comments.id", ondelete="CASCADE"), nullable=False
    )

    comment: Mapped["CommentModel"] = relationship("CommentModel", back_populates="likes")

    __table_args__ = (
        UniqueConstraint("user_id", "comment_id", name="user_comment_like_unique"),
    )

class SubCommentLikeModel(Base):
    __tablename__ = "sub_comment_likes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    is_like: Mapped[bool] = mapped_column(Boolean, nullable=False)

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    sub_comment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("movies_sub_comments.id", ondelete="CASCADE"), nullable=False
    )

    sub_comment: Mapped["SubCommentModel"] = relationship("SubCommentModel", back_populates="likes")

    __table_args__ = (
        UniqueConstraint("user_id", "sub_comment_id", name="user_sub_comment_like_unique"),
    )