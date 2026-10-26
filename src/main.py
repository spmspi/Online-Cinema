from fastapi import FastAPI
from .lifespan import lifespan
from src.routers.movies import router

app = FastAPI(
    title="Cinema",
    description="Description of project",
    lifespan=lifespan
)
@app.get("/")
async def read_root():
    return {"message": "Hello, World!"}

app.include_router(router)