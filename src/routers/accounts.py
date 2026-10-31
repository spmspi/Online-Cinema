from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import EmailStr
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from datetime import datetime, timezone
from typing import cast
from src import settings
from src.database.models.accounts import (
    UserModel,
    UserGroupModel,
    UserGroupEnum,
    RefreshTokenModel,
)
from src.database.engine import get_db
from src.dependencies import get_jwt_auth_manager, get_current_user, get_admin_user_group
from src.schemas.accounts import (
    UserRegistrationRequestSchema,
    UserRegistrationResponseSchema,
    UserLoginResponseSchema,
    UserLoginRequestSchema,
    UserActivationRequestSchema,
    PasswordResetCompleteRequestSchema,
    MessageResponseSchema,
    GetAccessTokenResponseSchema,
    GetAccessTokenResponseSchema,
    GetAccessTokenRequestSchema,
    PasswordResetRequestSchema,
    ActivateAccountRequestSchema,
)
from src.database.models.accounts import ActivationTokenModel
from src.security.interface_token import JWTAuthManagerInterface
from src.dependencies import get_accounts_email_notificator
from src.notifications.interfaces import EmailSenderInterface

router = APIRouter()


@router.post("/register/")
async def register_user(
    user_data: UserRegistrationRequestSchema,
    db: AsyncSession = Depends(get_db),
    email_sender: EmailSenderInterface = Depends(get_accounts_email_notificator)
) -> UserRegistrationResponseSchema:

    stmt = select(UserModel).where(UserModel.email == user_data.email)
    result = await db.execute(stmt)
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A user with this email {user_data.email} already exists.",
        )

    stmt = select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.USER)
    result = await db.execute(stmt)
    user_group = result.scalars().first()
    if not user_group:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Default user group not found.",
        )

    try:
        new_user = UserModel.create(
            email=str(user_data.email),
            raw_password=user_data.password,
            group_id=user_group.id,
        )
        db.add(new_user)
        await db.flush()

        activation_token = ActivationTokenModel(user_id=new_user.id)
        db.add(activation_token)

        await db.commit()
        await db.refresh(new_user)
    except SQLAlchemyError as e:
        print(e)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during user creation.",
        ) from e
    else:
        activation_link = "http://127.0.0.1/accounts/activate/"

        await email_sender.send_activation_email(
            new_user.email,
            activation_link
        )

    return UserRegistrationResponseSchema.model_validate(new_user)


@router.post(
    "/login/",
    response_model=UserLoginResponseSchema,
)
async def login_user(
    login_data: UserLoginRequestSchema,
    db: AsyncSession = Depends(get_db),
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
) -> UserLoginResponseSchema:

    stmt = select(UserModel).filter_by(email=login_data.email)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user or not user.verify_password(login_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not activated.",
        )

    jwt_refresh_token = jwt_manager.create_refresh_token({"user_id": user.id})

    try:
        refresh_token = RefreshTokenModel.create(
            user_id=user.id,
            days_valid=settings.LOGIN_TIME_DAYS,
            token=jwt_refresh_token,
        )
        db.add(refresh_token)
        await db.flush()
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the request.",
        )

    jwt_access_token = jwt_manager.create_access_token({"user_id": user.id})
    return UserLoginResponseSchema(
        access_token=jwt_access_token,
        refresh_token=jwt_refresh_token,
    )


@router.post(
    "/activate/",
    response_model=MessageResponseSchema,
)
async def activate_account(
    activation_data: UserActivationRequestSchema,
    db: AsyncSession = Depends(get_db),
    email_sender: EmailSenderInterface = Depends(get_accounts_email_notificator)
) -> MessageResponseSchema:

    stmt = (
        select(ActivationTokenModel)
        .options(joinedload(ActivationTokenModel.user))
        .join(UserModel)
        .where(
            UserModel.email == activation_data.email,
            ActivationTokenModel.token == activation_data.token,
        )
    )
    result = await db.execute(stmt)
    token_record = result.scalars().first()

    now_utc = datetime.now(timezone.utc)
    if (
        not token_record
        or cast(datetime, token_record.expires_at).replace(tzinfo=timezone.utc)
        < now_utc
    ):
        if token_record:
            await db.delete(token_record)
            await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired activation token.",
        )

    user = token_record.user
    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is already active.",
        )

    user.is_active = True
    await db.delete(token_record)
    await db.commit()

    login_link = "http://127.0.0.1/accounts/login/"

    await email_sender.send_activation_complete_email(
        str(activation_data.email),
        login_link
    )

    return MessageResponseSchema(message="User account activated successfully.")


@router.post(
    "/get_token/",
    response_model=GetAccessTokenResponseSchema,
)
async def get_access_token(
    payload: GetAccessTokenRequestSchema,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(UserModel)
        .filter_by(email=payload.email)
        .options(joinedload(UserModel.activation_token))
    )
    result = await db.execute(stmt)
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email",
        )
    token = user.activation_token.token
    return GetAccessTokenResponseSchema(access_token=token)


@router.post(
    "/password-reset/request/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def request_password_reset_token(
    data: PasswordResetRequestSchema,
    db: AsyncSession = Depends(get_db),
    email_sender: EmailSenderInterface = Depends(get_accounts_email_notificator)
) -> MessageResponseSchema:

    stmt = select(UserModel).filter_by(email=data.email)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user or not user.is_active:
        return MessageResponseSchema(
            message="If you are registered, you will receive an email with instructions."
        )

    await db.execute(
        delete(PasswordResetTokenModel).where(
            PasswordResetTokenModel.user_id == user.id
        )
    )

    reset_token = PasswordResetTokenModel(user_id=cast(int, user.id))
    db.add(reset_token)
    await db.commit()

    password_reset_complete_link = "http://127.0.0.1/accounts/password-reset-complete/"

    await email_sender.send_password_reset_email(
        str(data.email),
        password_reset_complete_link
    )

    return MessageResponseSchema(
        message="If you are registered, you will receive an email with instructions."
    )


@router.post(
    "/reset-password/complete/",
    response_model=MessageResponseSchema,
)
async def reset_password(
    data: PasswordResetCompleteRequestSchema,
    db: AsyncSession = Depends(get_db),
    email_sender: EmailSenderInterface = Depends(get_accounts_email_notificator)
) -> MessageResponseSchema:
    stmt = select(UserModel).filter_by(email=data.email)
    result = await db.execute(stmt)
    user = result.scalars().first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email or token."
        )

    stmt = select(PasswordResetTokenModel).filter_by(user_id=user.id)
    result = await db.execute(stmt)
    token_record = result.scalars().first()

    if not token_record or token_record.token != data.token:
        if token_record:
            await db.run_sync(lambda s: s.delete(token_record))
            await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email or token."
        )

    expires_at = cast(datetime, token_record.expires_at).replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        await db.run_sync(lambda s: s.delete(token_record))
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email or token."
        )

    try:
        user.password = data.password
        await db.run_sync(lambda s: s.delete(token_record))
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while resetting the password.",
        )

    login_link = "http://127.0.0.1/accounts/login/"

    await email_sender.send_password_reset_complete_email(
        str(data.email),
        login_link
    )

    return MessageResponseSchema(message="Password reset successfully.")


@router.post(
    "/logout/",
    response_model=MessageResponseSchema,
)
async def logout_user(
        user: UserModel = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    stmt = select(RefreshTokenModel).filter_by(user_id=user.id)
    result = await db.execute(stmt)
    token = result.scalars().first()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user",
        )
    await db.delete(token)
    await db.commit()
    return MessageResponseSchema(message="Logout successfully.")

@router.post(
    "/activate_account_for_admin/",
    response_model=MessageResponseSchema,
)
async def activate_account_for_admin(
        email: ActivateAccountRequestSchema,
        db: AsyncSession = Depends(get_db),
        is_admin: UserModel = Depends(get_admin_user_group)
):
    stmt = select(UserModel).filter_by(email=email.email)
    result = await db.execute(stmt)
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    if user.is_active == True:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account is already activated.",
        )
    user.is_active = True
    await db.commit()
    return MessageResponseSchema(message="Activated successfully.")

