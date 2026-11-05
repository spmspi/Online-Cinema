from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from src.database.models.movies import MovieModel, CertificationModel, GenreModel, DirectorModel, StarModel
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


    cert_pg13 = CertificationModel(name="PG-13")
    cert_r = CertificationModel(name="R")

    session.add_all([cert_pg13, cert_r])
    await session.flush()


    action_genre = GenreModel(name="Action")
    scifi_genre = GenreModel(name="Sci-Fi")
    drama_genre = GenreModel(name="Drama")


    nolan = DirectorModel(name="Christopher Nolan")
    wachowski = DirectorModel(name="Lana Wachowski")


    dicaprio = StarModel(name="Leonardo DiCaprio")
    matthew = StarModel(name="Matthew McConaughey")
    keanu = StarModel(name="Keanu Reeves")


    movie1 = MovieModel(
        uuid_movie=uuid.uuid4(),
        name="Inception",
        year=2010,
        time=148,
        imdb=8.8,
        votes=2400000,
        meta_score=74.0,
        gross=836.8,
        description="A thief who steals corporate secrets through the use of dream-sharing technology...",
        price=14.99,
        certification_id=cert_pg13.id,
        genres=[action_genre, scifi_genre, drama_genre],
        directors=[nolan],
        stars=[dicaprio]
    )

    movie2 = MovieModel(
        uuid_movie=uuid.uuid4(),
        name="Interstellar",
        year=2014,
        time=169,
        imdb=8.7,
        votes=1900000,
        meta_score=74.0,
        gross=677.8,
        description="A team of explorers travel through a wormhole in space in an attempt to ensure humanity's survival.",
        price=16.99,
        certification_id=cert_pg13.id,
        genres=[scifi_genre, drama_genre],
        directors=[nolan],
        stars=[matthew]
    )

    movie3 = MovieModel(
        uuid_movie=uuid.uuid4(),
        name="The Matrix",
        year=1999,
        time=136,
        imdb=8.7,
        votes=1900000,
        meta_score=73.0,
        gross=465.3,
        description="When a beautiful stranger leads computer hacker Neo to a forbidding underworld...",
        price=12.99,
        certification_id=cert_r.id,
        genres=[action_genre, scifi_genre],
        directors=[wachowski],
        stars=[keanu]
    )

    session.add_all([movie1, movie2, movie3])
    await session.commit()



@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await init_default_groups()
    await init_test_movies(AsyncPostgresqlSessionLocal())
    yield

app = FastAPI(lifespan=lifespan)
