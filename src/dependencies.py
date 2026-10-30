from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.testing.pickleable import User
from fastapi.security import OAuth2PasswordBearer

from src.database.models.accounts import UserGroupModel, UserGroupEnum
from src.database.engine import settings, get_db
from src.database.models.accounts import UserModel
from src.security.interface_token import JWTAuthManagerInterface
from src.security.token_manager import JWTAuthManager
from src.settings import Settings, get_settings
from src.storage.interfaces import S3StorageInterface
from src.storage.s3 import S3StorageClient


def get_jwt_auth_manager(settings: Settings = Depends(get_settings)) -> JWTAuthManagerInterface:

    return JWTAuthManager(
        secret_key_access=settings.SECRET_KEY_ACCESS,
        secret_key_refresh=settings.SECRET_KEY_REFRESH,
        algorithm=settings.JWT_SIGNING_ALGORITHM
    )

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=settings.ACCESS_TOKEN_URL,
)


def get_s3_storage_client(
    settings: Settings = Depends(get_settings)
) -> S3StorageInterface:
    """
    Retrieve an instance of the S3StorageInterface configured with the application settings.

    This function instantiates an S3StorageClient using the provided settings, which include the S3 endpoint URL,
    access credentials, and the bucket name. The returned client can be used to interact with an S3-compatible
    storage service for file uploads and URL generation.

    Args:
        settings (BaseAppSettings, optional): The application settings,
        provided via dependency injection from `get_settings`.

    Returns:
        S3StorageInterface: An instance of S3StorageClient configured with the appropriate S3 storage settings.
    """
    return S3StorageClient(
        endpoint_url=settings.S3_STORAGE_ENDPOINT,
        access_key=settings.S3_STORAGE_ACCESS_KEY,
        secret_key=settings.S3_STORAGE_SECRET_KEY,
        bucket_name=settings.S3_BUCKET_NAME
    )


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)],
                           db: AsyncSession = Depends(get_db),
                           jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager)):
    payload = jwt_manager.decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=401,
        )
    user_id = payload.get("user_id")
    stmt = select(UserModel).where(UserModel.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found",
        )
    return user


async def get_user_group(current_user: User = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
    stmt = (
        select(UserModel)
        .where(UserModel.id == current_user.id)
        .options(joinedload(UserModel.group))
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    allowed_roles = [UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR]
    if not user.group or user.group.name not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail="insufficient permissions for these actions",
        )
    return user