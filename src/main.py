from fastapi import FastAPI
from .lifespan import lifespan
from src.routers.movies import router as movies_router
from src.routers.accounts import router as accounts_router
from src.routers.profiles import router as profiles_router

app = FastAPI(
    title="Cinema",
    description="Description of project",
    lifespan=lifespan
)


app.include_router(movies_router)
app.include_router(accounts_router)
app.include_router(profiles_router)