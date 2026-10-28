import os
from dotenv import load_dotenv

load_dotenv()

POSTGRES_USER: str = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD")
POSTGRES_HOST: str = os.getenv("POSTGRES_HOST")
POSTGRES_DB_PORT: int = int(os.getenv("POSTGRES_DB_PORT", 5432))
POSTGRES_DB: str = os.getenv("POSTGRES_DB")

SECRET_KEY_ACCESS: str = os.getenv("SECRET_KEY_ACCESS")
SECRET_KEY_REFRESH: str = os.getenv("SECRET_KEY_REFRESH")
ALGORITHM: str = os.getenv("ALGORITHM")