from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.testing.pickleable import User
from fastapi.security import OAuth2PasswordBearer

from src.database.engine import settings, get_db
from src.database.models.accounts import UserModel
from src.security.interface_token import JWTAuthManagerInterface
from src.security.token_manager import JWTAuthManager
from src.settings import Settings, get_settings


def get_jwt_auth_manager(settings: Settings = Depends(get_settings)) -> JWTAuthManagerInterface:

    return JWTAuthManager(
        secret_key_access=settings.SECRET_KEY_ACCESS,
        secret_key_refresh=settings.SECRET_KEY_REFRESH,
        algorithm=settings.JWT_SIGNING_ALGORITHM
    )

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=settings.ACCESS_TOKEN_URL,
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