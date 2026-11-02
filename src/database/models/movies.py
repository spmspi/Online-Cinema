import uuid
from typing import List

from sqlalchemy import Column, Integer, String, Float, DECIMAL, ForeignKey, Table, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy.dialects import postgresql as psql

from .accounts import UserModel
from .base import Base

MovieGenresModel = Table(
    "movie_genres",
    Base.metadata,
    Column(
        "movie_id",
        Integer,
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "genre_id",
        Integer,
        ForeignKey("genres.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
)

MovieStarsModel = Table(
    "movie_stars",
    Base.metadata,
    Column(
        "movie_id",
        Integer,
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "star_id",
        Integer,
        ForeignKey("stars.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
)

MovieDirectorModel = Table(
    "movie_directors",
    Base.metadata,
    Column(
        "movie_id",
        Integer,
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "director_id",
        Integer,
        ForeignKey("directors.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
)


class GenreModel(Base):
    __tablename__ = "genres"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = Column(String, nullable=False, unique=True)
    movies = relationship("MovieModel", secondary=MovieGenresModel, back_populates="genres")

class StarModel(Base):
    __tablename__ = "stars"
    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = Column(String, nullable=False, unique=True)
    movies = relationship("MovieModel", secondary=MovieStarsModel, back_populates="stars")


class DirectorModel(Base):
    __tablename__ = "directors"
    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = Column(String, nullable=False, unique=True)
    movies = relationship("MovieModel", secondary=MovieDirectorModel, back_populates="directors")


class CertificationModel(Base):
    __tablename__ = "certifications"
    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = Column(String, nullable=False, unique=True)
    movies: Mapped[list["MovieModel"]] = relationship(
        "MovieModel", back_populates="certification"
    )


class MovieModel(Base):
    __tablename__ = "movies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uuid_movie: Mapped[uuid.UUID] = mapped_column(
        psql.UUID(as_uuid=True),
        unique=True,
        default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    time: Mapped[int] = mapped_column(Integer, nullable=False)
    imdb: Mapped[float] = mapped_column(Float, nullable=False)
    votes: Mapped[int] = mapped_column(Integer, nullable=False)
    meta_score: Mapped[float] = mapped_column(Float, default=0.0)
    gross: Mapped[float] = mapped_column(Float)
    description: Mapped[str] = mapped_column(String)
    price: Mapped[float] = mapped_column(DECIMAL(10, 2))
    certification_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("certifications.id"), nullable=False
    )
    certification: Mapped["CertificationModel"] = relationship(
        "CertificationModel", back_populates="movies"
    )
    genres: Mapped[list["GenreModel"]] = relationship(
        "GenreModel", secondary=MovieGenresModel, back_populates="movies"
    )
    stars: Mapped[list["StarModel"]] = relationship(
        "StarModel", secondary=MovieStarsModel, back_populates="movies"
    )
    directors: Mapped[list["DirectorModel"]] = relationship(
        "DirectorModel", secondary=MovieDirectorModel, back_populates="movies"
    )

    @classmethod
    def default_order_by(cls):
        return [cls.id.desc()]


class MovieRatingModel(Base):
    __tablename__ = "movie_ratings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    movie_id: Mapped[int] = mapped_column(Integer, ForeignKey("movies.id", ondelete="CASCADE"))

    movie: Mapped["MovieModel"] = relationship("MovieModel")

    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 10", name="meta_score"),
        UniqueConstraint("user_id", "movie_id", name="user_movie_rating"),
    )



