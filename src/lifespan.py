from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import select
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await init_default_groups()
    yield

app = FastAPI(lifespan=lifespan)
