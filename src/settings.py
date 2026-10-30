import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


def get_settings():
    return Settings()

class BaseAppSettings(BaseSettings):
    pass

LOGIN_TIME_DAYS: int = 7

class Settings(BaseAppSettings):
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "test_user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "test_password")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "test_host")
    POSTGRES_DB_PORT: int = int(os.getenv("POSTGRES_DB_PORT", 5432))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "test_db")

    S3_STORAGE_HOST: str = os.getenv("MINIO_HOST", "minio-cinema")
    S3_STORAGE_PORT: int = os.getenv("MINIO_PORT", 9000)
    S3_STORAGE_ACCESS_KEY: str = os.getenv("MINIO_ROOT_USER", "minioadmin")
    S3_STORAGE_SECRET_KEY: str = os.getenv("MINIO_ROOT_PASSWORD", "some_password")
    S3_BUCKET_NAME: str = os.getenv("MINIO_STORAGE", "cinema-storage")

    LOGIN_TIME_DAYS: int = 7

    SECRET_KEY_ACCESS: str = os.getenv("SECRET_KEY_ACCESS", os.urandom(32))
    SECRET_KEY_REFRESH: str = os.getenv("SECRET_KEY_REFRESH", os.urandom(32))
    JWT_SIGNING_ALGORITHM: str = os.getenv("JWT_SIGNING_ALGORITHM", "HS256")
    ACCESS_TOKEN_URL: str = os.getenv("ACCESS_TOKEN_URL", "http://127.0.0.1:8000/login/")

    @property
    def S3_STORAGE_ENDPOINT(self) -> str:
        return f"http://{self.S3_STORAGE_HOST}:{self.S3_STORAGE_PORT}"