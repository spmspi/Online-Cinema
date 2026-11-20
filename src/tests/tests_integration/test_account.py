import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import select, delete, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from src.database.models.accounts import (
    UserModel,
    ActivationTokenModel,
    PasswordResetTokenModel,
    UserGroupModel,
    UserGroupEnum,
    RefreshTokenModel
)


@pytest.mark.asyncio
async def test_register_user_success(client, db_session, seed_user_groups):
    """
    Test successful user registration.

    Validates that a new user and an activation token are created in the database.
    """
    payload = {
        "email": "testuser@example.com",
        "password": "StrongPassword123!"
    }

    response = await client.post("/register/", json=payload)
    assert response.status_code == 201, "Expected status code 201 Created."
    response_data = response.json()
    assert response_data["email"] == payload["email"], "Returned email does not match."
    assert "id" in response_data, "Response does not contain user ID."

    stmt_user = select(UserModel).where(UserModel.email == payload["email"])
    result = await db_session.execute(stmt_user)
    created_user = result.scalars().first()
    assert created_user is not None, "User was not created in the database."
    assert created_user.email == payload["email"], "Created user's email does not match."

    stmt_token = select(ActivationTokenModel).where(ActivationTokenModel.user_id == created_user.id)
    result = await db_session.execute(stmt_token)
    activation_token = result.scalars().first()
    assert activation_token is not None, "Activation token was not created in the database."
    assert activation_token.user_id == created_user.id, "Activation token's user_id does not match."
    assert activation_token.token is not None, "Activation token has no token value."

    expires_at = activation_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    assert expires_at > datetime.now(timezone.utc), "Activation token is already expired."



@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_password, expected_error", [
    ("short", "Password must contain at least 8 characters."),
    ("NoDigitHere!", "Password must contain at least one digit."),
    ("nodigitnorupper@", "Password must contain at least one uppercase letter."),
    ("NOLOWERCASE1@", "Password must contain at least one lower letter."),
    ("NoSpecial123", "Password must contain at least one special character: @, $, !, %, *, ?, #, &."),
])
async def test_register_user_password_validation(client, seed_user_groups, invalid_password, expected_error):
    """
    Test password strength validation in the user registration endpoint.

    Ensures that when an invalid password is provided, the endpoint returns the appropriate
    error message and a 422 status code.

    Args:
        client: The asynchronous HTTP client fixture.
        seed_user_groups: Fixture that seeds the default user groups.
        invalid_password (str): The password to test.
        expected_error (str): The expected error message substring.
    """
    payload = {
        "email": "testuser@example.com",
        "password": invalid_password
    }

    response = await client.post("/register/", json=payload)
    assert response.status_code == 422, "Expected status code 422 for invalid input."

    response_data = response.json()
    assert expected_error in str(response_data), f"Expected error message: {expected_error}"



@pytest.mark.asyncio
async def test_register_user_internal_server_error(client, seed_user_groups):
    """
    Test server error during user registration.

    Ensures that a 500 Internal Server Error is returned when a database operation fails.

    This test patches the commit method of the AsyncSession to simulate a SQLAlchemyError,
    then verifies that the registration endpoint returns the appropriate HTTP 500 error
    with the expected error message.
    """
    payload = {
        "email": "erroruser@example.com",
        "password": "StrongPassword123!"
    }

    with patch("src.routers.accounts.AsyncSession.commit", side_effect=SQLAlchemyError):
        response = await client.post("/register/", json=payload)

        assert response.status_code == 500, "Expected status code 500 for internal server error."

        response_data = response.json()
        expected_message = "An error occurred during user creation."
        assert response_data["detail"] == expected_message, f"Expected error message: {expected_message}"


@pytest.mark.asyncio
async def test_activate_account_success(client, db_session, seed_user_groups):
    """
    Test successful activation of a user account.

    Steps:
    - Register a new user.
    - Verify the user is inactive.
    - Activate the user using the activation token.
    - Verify the user is activated and the token is deleted.
    """
    registration_payload = {
        "email": "testuser@example.com",
        "password": "StrongPassword123!"
    }

    registration_response = await client.post("/register/", json=registration_payload)
    assert registration_response.status_code == 201, "Expected status code 201 for successful registration."

    stmt = (
        select(UserModel)
        .options(joinedload(UserModel.activation_token))
        .where(UserModel.email == registration_payload["email"])
    )
    result = await db_session.execute(stmt)
    user = result.scalars().first()
    assert user is not None, "User was not created in the database."
    assert not user.is_active, "Newly registered user should not be active."

    assert user.activation_token is not None and user.activation_token.token is not None, \
        "Activation token was not created in the database."

    activation_payload = {
        "email": registration_payload["email"],
        "token": user.activation_token.token
    }

    activation_response = await client.post("/activate/", json=activation_payload)
    assert activation_response.status_code == 200, "Expected status code 200 for successful activation."
    assert activation_response.json()["message"] == "User account activated successfully."

    stmt = (
        select(UserModel)
        .options(joinedload(UserModel.activation_token))
        .where(UserModel.email == registration_payload["email"])
    )
    result = await db_session.execute(stmt)
    user = result.scalars().first()
    await db_session.refresh(user)
    assert user.is_active, "User should be active after successful activation."

    stmt = select(ActivationTokenModel).where(ActivationTokenModel.user_id == user.id)
    result = await db_session.execute(stmt)
    token = result.scalars().first()
    assert token is None, "Activation token should be deleted after successful activation."


@pytest.mark.asyncio
async def test_activate_user_with_expired_token(client, db_session, seed_user_groups):
    """
    Test activation with an expired token.

    Ensures that the endpoint returns a 400 error when the activation token is expired.
    Steps:
    - Register a new user.
    - Retrieve the user and their activation token.
    - Manually set the token's expiration to a past date.
    - Attempt to activate the account with the expired token.
    - Verify that the response is a 400 error with the expected error message.
    """
    registration_payload = {
        "email": "testuser@example.com",
        "password": "StrongPassword123!"
    }
    registration_response = await client.post("/register/", json=registration_payload)
    assert registration_response.status_code == 201, "Expected status code 201 for successful registration."

    stmt = select(UserModel).where(UserModel.email == registration_payload["email"])
    result = await db_session.execute(stmt)
    user = result.scalars().first()
    assert user is not None, "User should exist in the database."
    assert not user.is_active, "User should not be active before activation."

    stmt_token = select(ActivationTokenModel).where(ActivationTokenModel.user_id == user.id)
    result_token = await db_session.execute(stmt_token)
    activation_token = result_token.scalars().first()
    assert activation_token is not None, "Activation token should exist for the user."

    activation_token.expires_at = datetime.now(timezone.utc) - timedelta(days=2)
    await db_session.commit()

    activation_payload = {
        "email": registration_payload["email"],
        "token": activation_token.token
    }
    activation_response = await client.post("/activate/", json=activation_payload)

    assert activation_response.status_code == 400, "Expected status code 400 for expired token."
    assert activation_response.json()["detail"] == "Invalid or expired activation token.", (
        "Expected error message for expired token."
    )



@pytest.mark.asyncio
async def test_activate_user_with_deleted_token(client, db_session, seed_user_groups):
    """
    Test activation with a deleted token.

    Ensures that the endpoint returns a 400 error when the activation token has been deleted.

    Steps:
    - Register a new user.
    - Verify that the user is created and inactive.
    - Delete the activation token from the database.
    - Attempt to activate the account using the deleted token.
    - Verify that a 400 error is returned with the appropriate error message.
    """
    registration_payload = {
        "email": "testuser@example.com",
        "password": "StrongPassword123!"
    }
    registration_response = await client.post("/register/", json=registration_payload)
    assert registration_response.status_code == 201, "Expected status code 201 for successful registration."

    stmt = select(UserModel).where(UserModel.email == registration_payload["email"])
    result = await db_session.execute(stmt)
    user = result.scalars().first()
    assert user is not None, "User should exist in the database."
    assert not user.is_active, "User should not be active before activation."

    stmt_token = select(ActivationTokenModel).where(ActivationTokenModel.user_id == user.id)
    result_token = await db_session.execute(stmt_token)
    activation_token = result_token.scalars().first()
    assert activation_token is not None, "Activation token should exist for the user."

    token_value = activation_token.token

    await db_session.execute(
        delete(ActivationTokenModel).where(ActivationTokenModel.id == activation_token.id)
    )
    await db_session.commit()

    activation_payload = {
        "email": registration_payload["email"],
        "token": token_value
    }
    activation_response = await client.post("/activate/", json=activation_payload)
    assert activation_response.status_code == 400, "Expected status code 400 for deleted token."
    assert activation_response.json()["detail"] == "Invalid or expired activation token.", (
        "Expected error message for deleted token."
    )



@pytest.mark.asyncio
async def test_activate_already_active_user(client, db_session, seed_user_groups):
    """
    Test activation of an already active user.

    Ensures that the endpoint returns a 400 error if the user is already active.
    Steps:
    - Register a new user.
    - Mark the user as active in the database.
    - Attempt to activate the user using the activation token.
    - Verify that a 400 error with the expected error message is returned.
    """
    registration_payload = {
        "email": "testuser@example.com",
        "password": "StrongPassword123!"
    }

    registration_response = await client.post("/register/", json=registration_payload)
    assert registration_response.status_code == 201, "Expected status code 201 for successful registration."

    stmt = select(UserModel).where(UserModel.email == registration_payload["email"])
    result = await db_session.execute(stmt)
    user = result.scalars().first()
    assert user is not None, "User should exist in the database."

    user.is_active = True
    await db_session.commit()

    stmt_token = select(ActivationTokenModel).where(ActivationTokenModel.user_id == user.id)
    result_token = await db_session.execute(stmt_token)
    activation_token = result_token.scalars().first()
    assert activation_token is not None, "Activation token should exist for the user."

    activation_payload = {
        "email": registration_payload["email"],
        "token": activation_token.token
    }
    activation_response = await client.post("/activate/", json=activation_payload)
    assert activation_response.status_code == 400, "Expected status code 400 for already active user."
    assert activation_response.json()["detail"] == "User account is already active.", (
        "Expected error message for already active user."
    )

@pytest.mark.asyncio
async def test_logout_user(client, db_session, seed_user_groups):
    """
    Test for refresh token removal after logout
    It also verifies that the logout token is unique.
    Steps:
    - Register a new user.
    - Mark the user as active in the database.
    - we keep the old refresh token
    - Log out and log back in
    - We verify that the old and new tokens do not match.

    """
    registration_payload = {
        "email": "testuser@example.com",
        "password": "StrongPassword123!"
    }

    registration_response = await client.post("/register/", json=registration_payload)
    assert registration_response.status_code == 201, "Expected status code 201 for successful registration."

    stmt = select(UserModel).where(UserModel.email == registration_payload["email"])
    result = await db_session.execute(stmt)
    user = result.scalars().first()

    user.is_active = True
    await db_session.commit()
    await db_session.refresh(user)

    user_id = user.id

    login = await client.post("/login/", json=registration_payload)
    assert login.status_code == 200, "Expected status code 200 for successful login."

    response_data = login.json()
    header = response_data["access_token"]

    stmt = select(RefreshTokenModel).filter_by(user_id=user_id)
    result = await db_session.execute(stmt)
    token = result.scalars().first()

    assert token is not None, "Token should exist in the database."

    old_token = token.token

    assert user is not None, "User should exist in the database."

    logout = await client.post("/logout/", json={}, headers={"Authorization": f"Bearer {header}"})
    assert logout.status_code == 200, "Expected status code 200 for successful logout."

    await db_session.commit()
    await db_session.refresh(user)

    stmt = select(RefreshTokenModel).filter_by(user_id=user_id)
    result = await db_session.execute(stmt)
    token_after_logout = result.scalars().first()

    assert token_after_logout is None, "The refresh token must be deleted after logout."

    login = await client.post("/login/", json=registration_payload)
    assert login.status_code == 200, "Expected status code 200 for successful login."

    db_session.expire_all()

    stmt = select(RefreshTokenModel).filter_by(user_id=user_id)
    result = await db_session.execute(stmt)
    token_after_logout = result.scalars().first()

    assert token_after_logout.token != old_token, "After login, a new refresh token should be created."




@pytest.mark.asyncio
async def test_request_password_reset_token_success(client, db_session, seed_user_groups):
    """
    Test successful password reset token request.

    Ensures that a password reset token is created for an active user.

    Steps:
    - Register a new user.
    - Mark the user as active.
    - Request a password reset token.
    - Verify that the endpoint returns status 200 and the expected success message.
    - Query the database to confirm that a PasswordResetTokenModel record was created.
    - Verify that the token's expiration date is in the future.
    """
    registration_payload = {
        "email": "testuser@example.com",
        "password": "StrongPassword123!"
    }
    registration_response = await client.post("/register/", json=registration_payload)
    assert registration_response.status_code == 201, "Expected status code 201 for successful registration."

    stmt = select(UserModel).where(UserModel.email == registration_payload["email"])
    result = await db_session.execute(stmt)
    user = result.scalars().first()
    assert user is not None, "User should exist in the database."

    user.is_active = True
    await db_session.commit()

    reset_payload = {"email": registration_payload["email"]}
    reset_response = await client.post("/password-reset/request/", json=reset_payload)
    assert reset_response.status_code == 200, "Expected status code 200 for successful token request."
    assert reset_response.json()["message"] == "If you are registered, you will receive an email with instructions.", \
        "Expected success message for password reset token request."

    stmt_token = select(PasswordResetTokenModel).where(PasswordResetTokenModel.user_id == user.id)
    result_token = await db_session.execute(stmt_token)
    reset_token = result_token.scalars().first()
    assert reset_token is not None, "Password reset token should be created for the user."

    expires_at = reset_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    assert expires_at > datetime.now(timezone.utc), "Password reset token should have a future expiration date."


@pytest.mark.asyncio
async def test_request_password_reset_token_nonexistent_user(client, db_session):
    """
    Test password reset token request for a non-existent user.

    Ensures that the endpoint responds with a generic success message and that no password reset token is created
    when the email does not exist in the database.
    """
    reset_payload = {"email": "nonexistent@example.com"}

    reset_response = await client.post("/password-reset/request/", json=reset_payload)
    assert reset_response.status_code == 200, "Expected status code 200 for non-existent user request."
    assert reset_response.json()["message"] == "If you are registered, you will receive an email with instructions.", (
        "Expected generic success message for non-existent user request."
    )

    stmt = select(func.count(PasswordResetTokenModel.id))
    result = await db_session.execute(stmt)
    reset_token_count = result.scalar_one()
    assert reset_token_count == 0, "No password reset token should be created for non-existent user."


@pytest.mark.asyncio
async def test_request_password_reset_token_for_inactive_user(client, db_session, seed_user_groups):
    """
    Test password reset token request for a registered but inactive user.

    Ensures that the endpoint returns the generic success message and that no password reset token
    is created when the user is registered but inactive.
    """
    registration_payload = {
        "email": "inactiveuser@example.com",
        "password": "StrongPassword123!"
    }
    registration_response = await client.post("/register/", json=registration_payload)
    assert registration_response.status_code == 201, "Expected status code 201 for successful registration."

    stmt = select(UserModel).where(UserModel.email == registration_payload["email"])
    result = await db_session.execute(stmt)
    created_user = result.scalars().first()
    assert created_user is not None, "User should be created in the database."
    assert not created_user.is_active, "User should not be active after registration."

    reset_payload = {"email": registration_payload["email"]}
    reset_response = await client.post("/password-reset/request/", json=reset_payload)
    assert reset_response.status_code == 200, "Expected status code 200 for inactive user password reset request."
    assert reset_response.json()["message"] == "If you are registered, you will receive an email with instructions.", (
        "Expected generic success message for inactive user password reset request."
    )

    stmt_tokens = select(func.count(PasswordResetTokenModel.id))
    result_tokens = await db_session.execute(stmt_tokens)
    reset_token_count = result_tokens.scalar_one()
    assert reset_token_count == 0, "No password reset token should be created for an inactive user."




