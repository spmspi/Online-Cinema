from fastapi import FastAPI

from src.routers.movies import router

app = FastAPI()

@app.get("/")
async def read_root():
    return {"message": "Hello, World!"}

app.include_router(router)