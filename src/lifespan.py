from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.database.models.base import Base
from src.database.engine import engine



@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(lifespan=lifespan)
