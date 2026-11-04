from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.testing.pickleable import User

from src.dependencies.service import get_jwt_auth_manager, oauth2_scheme
from src.database.models.accounts import UserGroupEnum
from src.database.engine import get_db
from src.database.models.accounts import UserModel
from src.security.interface_token import JWTAuthManagerInterface
from src.exceptions.security import BaseSecurityError


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db),
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
):
    try:
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
    except BaseSecurityError:
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions",
        )


async def get_user_group(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
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


async def get_admin_user_group(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(UserModel)
        .where(UserModel.id == current_user.id)
        .options(joinedload(UserModel.group))
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user.group or user.group.name not in UserGroupEnum.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="insufficient permissions for these actions",
        )
    return user
