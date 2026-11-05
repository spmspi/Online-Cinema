from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import random

from src.database.models.movies import (
    MovieModel,
    CertificationModel,
    GenreModel,
    DirectorModel,
    StarModel,
)
from src.session_postgres import AsyncPostgresqlSessionLocal
from src.database.models.base import Base
from src.database.engine import engine
from src.database.models.accounts import UserGroupModel


async def init_default_groups():

    default_groups = ["admin", "user", "moderator"]

    async with AsyncPostgresqlSessionLocal() as session:
        for group_name in default_groups:
            stmt = select(UserGroupModel).where(UserGroupModel.name == group_name)
            result = await session.execute(stmt)
            existing_group = result.scalar_one_or_none()

            if not existing_group:

                new_group = UserGroupModel(name=group_name)
                session.add(new_group)

        await session.commit()


async def init_test_movies(session: AsyncSession):
    result = await session.execute(select(MovieModel))
    if result.first():
        return

    cert_g = CertificationModel(name="G")
    cert_pg = CertificationModel(name="PG")
    cert_pg13 = CertificationModel(name="PG-13")
    cert_r = CertificationModel(name="R")
    session.add_all([cert_g, cert_pg, cert_pg13, cert_r])
    await session.flush()
    certifications = [cert_g, cert_pg, cert_pg13, cert_r]

    genres_list = [
        GenreModel(name="Action"),
        GenreModel(name="Sci-Fi"),
        GenreModel(name="Drama"),
        GenreModel(name="Comedy"),
        GenreModel(name="Thriller"),
        GenreModel(name="Adventure"),
        GenreModel(name="Crime"),
        GenreModel(name="Fantasy"),
    ]
    session.add_all(genres_list)

    directors_list = [
        DirectorModel(name="Christopher Nolan"),
        DirectorModel(name="Denis Villeneuve"),
        DirectorModel(name="Quentin Tarantino"),
        DirectorModel(name="Martin Scorsese"),
        DirectorModel(name="David Fincher"),
        DirectorModel(name="Steven Spielberg"),
        DirectorModel(name="Ridley Scott"),
        DirectorModel(name="The Wachowskis"),
    ]
    session.add_all(directors_list)

    stars_list = [
        StarModel(name="Leonardo DiCaprio"),
        StarModel(name="Matthew McConaughey"),
        StarModel(name="Keanu Reeves"),
        StarModel(name="Tom Hardy"),
        StarModel(name="Brad Pitt"),
        StarModel(name="Christian Bale"),
        StarModel(name="Scarlett Johansson"),
        StarModel(name="Morgan Freeman"),
        StarModel(name="Cillian Murphy"),
        StarModel(name="Ryan Gosling"),
    ]
    session.add_all(stars_list)
    await session.flush()

    adjectives = [
        "The",
        "Beyond",
        "Last",
        "Hidden",
        "Secret",
        "Lost",
        "Return of the",
        "Rise of the",
        "Chronicles of",
        "Dark",
    ]
    nouns = [
        "Galaxy",
        "Future",
        "Shadow",
        "Empire",
        "Matrix",
        "Journey",
        "Hero",
        "City",
        "Ocean",
        "Planet",
        "Code",
        "Mission",
    ]

    movies_to_add = []
    for i in range(1, 101):

        movie_name = f"{random.choice(adjectives)} {random.choice(nouns)} {i}"

        movie = MovieModel(
            uuid_movie=uuid.uuid4(),
            name=movie_name,
            year=random.randint(1995, 2026),
            time=random.randint(90, 180),
            imdb=round(random.uniform(5.5, 9.3), 1),
            votes=random.randint(10000, 2500000),
            meta_score=round(random.uniform(50.0, 95.0), 1),
            gross=round(random.uniform(20.5, 900.0), 1),
            description=f"This is a generated test description for the movie {movie_name}. An epic story about adventure, mystery, and survival in a changing world.",
            price=round(random.uniform(9.99, 24.99), 2),
            certification_id=random.choice(certifications).id,
            genres=random.sample(genres_list, k=random.randint(1, 3)),
            directors=random.sample(directors_list, k=1),
            stars=random.sample(stars_list, k=random.randint(1, 2)),
        )
        movies_to_add.append(movie)

    session.add_all(movies_to_add)
    await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await init_default_groups()
    await init_test_movies(AsyncPostgresqlSessionLocal())
    yield


app = FastAPI(lifespan=lifespan)
