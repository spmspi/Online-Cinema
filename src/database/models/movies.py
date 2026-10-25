from typing import List

from sqlalchemy import Column, Integer, String, Float, DECIMAL, ForeignKey, Table
from sqlalchemy.orm import mapped_column, Mapped, relationship

from .base import Base

MoviesGenresModel = Table(
    "movies_genres",
    Base.metadata,
    Column("movie_id", Integer, ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True, nullable=False),
    Column("genre_id", Integer, ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True, nullable=False),
)

MovieStarsModel = Table(
    "movie_stars",
    Base.metadata,
    Column("movie_id", Integer, ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True, nullable=False),
    Column("star_id", Integer, ForeignKey("stars.id", ondelete="CASCADE"), primary_key=True, nullable=False),
)

class GenreModel(Base):
    __tablename__ = "genres"

    id: Mapped[int] = Column(Integer, primary_key=True)
    name: Mapped[str] = Column(String, nullable=False, unique=True)

class StarModel(Base):
    __tablename__ = "stars"
    id: Mapped[int] = Column(Integer, primary_key=True)
    name: Mapped[str] = Column(String, nullable=False, unique=True)


class MovieModel(Base):
    __tablename__ = "movies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uuid: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    time: Mapped[int] = mapped_column(Integer, nullable=False)
    imdb: Mapped[float] = mapped_column(Float, nullable=False)
    votes: Mapped[int] = mapped_column(Integer, nullable=False)
    meta_score: Mapped[float] = mapped_column(Float)
    gross: Mapped[float] = mapped_column(Float)
    description: Mapped[str] = mapped_column(String)
    price: Mapped[float] = mapped_column(DECIMAL(10, 2))
    certification_id: Mapped[int] = mapped_column(Integer, ForeignKey("certifications.id"))
    genres: Mapped[list["GenreModel"]] = relationship(
        "GenreModel",
        secondary=MoviesGenresModel,
        back_populates="movies"
    )
    actors: Mapped[list["GenreModel"]] = relationship(
        "StarModel",
        secondary=MovieStarsModel,
        back_populates="stars"
    )


class CertificationModel(Base):
    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
