import random
from decimal import Decimal

import pytest
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload, selectinload

from src.database import UserGroupModel, UserGroupEnum, UserModel
from src.schemas.accounts import UserRoleEnum
from src.database import MovieModel, DirectorModel
from src.database import (
    GenreModel,
    StarModel,
    CertificationModel,
)
from src.tests.service_tests import AuthTestHelper


@pytest.mark.asyncio
async def test_create_movie_and_related_models(client, db_session):
    """
    Test that a new movie is created successfully and related models
    (genres, stars, certification, ) are created if they do not exist.
    """
    auth = AuthTestHelper(client, db_session)
    headers = await auth.get_auth_headers(group_name=UserGroupEnum.ADMIN)

    movie_data = {
        "name": "New Movie",
        "year": 2025,
        "time": 120,
        "imdb": 4.5,
        "meta_score": 85.5,
        "votes": 1000,
        "description": "An amazing movie.",
        "price": 500.00,
        "gross": 1000000.00,
        "certification": "PG",
        "genres": ["Action", "Adventure"],
        "stars": ["John Doe", "Jane Doe"],
        "directors": ["Christopher Nolan", "Quentin Tarantino"]
    }

    response = await client.post("/admin/movies/", json=movie_data, headers=headers)
    assert response.status_code == 201, f"Expected status code 201, but got {response.status_code}"

    response_data = response.json()
    assert response_data["name"] == movie_data["name"], "Movie name does not match."
    assert response_data["year"] == movie_data["year"], "Movie year does not match."
    assert response_data["meta_score"] == movie_data["meta_score"], "Movie meta_score does not match."
    assert response_data["time"] == movie_data["time"], "Movie time does not match."
    assert response_data["imdb"] == movie_data["imdb"], "Movie imdb does not match."
    assert response_data["votes"] == movie_data["votes"], "Movie votes does not match."
    assert response_data["price"] == movie_data["price"], "Movie price does not match."
    assert response_data["gross"] == movie_data["gross"], "Movie gross does not match."

    for genre_name in movie_data["genres"]:
        stmt = select(GenreModel).where(GenreModel.name == genre_name)
        result = await db_session.execute(stmt)
        genre = result.scalars().first()
        assert genre is not None, f"Genre '{genre_name}' was not created."

    for star_name in movie_data["stars"]:
        stmt = select(StarModel).where(StarModel.name == star_name)
        result = await db_session.execute(stmt)
        star = result.scalars().first()
        assert star is not None, f"Actor '{star_name}' was not created."

    for director_name in movie_data["directors"]:
        stmt = select(DirectorModel).where(DirectorModel.name == director_name)
        result = await db_session.execute(stmt)
        director = result.scalars().first()
        assert director is not None, f"Language '{director_name}' was not created."

    stmt = select(CertificationModel).where(CertificationModel.name == movie_data["certification"])
    result = await db_session.execute(stmt)
    director = result.scalars().first()
    assert director is not None, f"Certification: '{movie_data['certification']}' was not created."



@pytest.mark.asyncio
async def test_create_movie_duplicate_error(client, db_session, seed_database):
    """
    Test that trying to create a movie with the same name and date as an existing movie
    results in a 409 conflict error.
    """
    auth = AuthTestHelper(client, db_session)
    headers = await auth.get_auth_headers(group_name=UserGroupEnum.ADMIN)

    stmt = select(MovieModel).limit(1)
    result = await db_session.execute(stmt)
    existing_movie = result.scalars().first()
    assert existing_movie is not None, "No existing movies found in the database."

    movie_data = {
        "name": existing_movie.name,
        "year": existing_movie.year,
        "time": existing_movie.time,
        "imdb": 4.5,
        "meta_score": 85.5,
        "votes": 1000,
        "description": "An amazing movie.",
        "price": 500.00,
        "gross": 1000000.00,
        "certification": "PG",
        "genres": ["Action", "Adventure"],
        "stars": ["John Doe", "Jane Doe"],
        "directors": ["Christopher Nolan", "Quentin Tarantino"]
    }

    response = await client.post("/admin/movies/", json=movie_data, headers=headers)
    assert response.status_code == 409, f"Expected status code 409, but got {response.status_code}"

    response_data = response.json()
    expected_detail = (
        f"A movie with the name '{movie_data['name']}', release date "
        f"'{movie_data['year']}', and {movie_data['time']} minute already exists."
    )
    assert response_data["detail"] == expected_detail, (
        f"Expected detail message: {expected_detail}, but got: {response_data['detail']}"
    )

@pytest.mark.asyncio
async def test_delete_movie_success(client, db_session, seed_database):
    """
    Test the `/movies/{movie_id}/` endpoint for successful movie deletion.
    """
    user_payload = {
        "email": "testuser@example.com",
        "password": "StrongPassword123!"
    }

    auth = AuthTestHelper(client, db_session)
    headers = await auth.get_auth_headers(group_name=UserGroupEnum.ADMIN)

    stmt = select(MovieModel).limit(1)
    result = await db_session.execute(stmt)
    movie = result.scalars().first()
    assert movie is not None, "No movies found in the database to delete."

    movie_id = movie.id

    response = await client.delete(f"/admin/movies/{movie_id}/", headers=headers)
    assert response.status_code == 204, f"Expected status code 204, but got {response.status_code}"

    stmt_check = select(MovieModel).where(MovieModel.id == movie_id)
    result_check = await db_session.execute(stmt_check)
    deleted_movie = result_check.scalars().first()
    assert deleted_movie is None, f"Movie with ID {movie_id} was not deleted."


@pytest.mark.asyncio
async def test_delete_movie_not_found(client, db_session):
    """
    Test the `/admin/movies/{movie_id}/` endpoint with a non-existent movie ID.
    """
    auth = AuthTestHelper(client, db_session)
    headers = await auth.get_auth_headers(group_name=UserGroupEnum.ADMIN)

    non_existent_id = 99999

    response = await client.delete(f"/admin/movies/{non_existent_id}/", headers=headers)
    assert response.status_code == 404, f"Expected status code 404, but got {response.status_code}"

    response_data = response.json()
    expected_detail = "Movie with the given ID was not found."
    assert response_data["detail"] == expected_detail, (
        f"Expected detail message: {expected_detail}, but got: {response_data['detail']}"
    )

@pytest.mark.asyncio
async def test_delete_movie_no_permissions(client, db_session, seed_database):
    """Test the `/admin/movies/{movie_id}/` endpoint with a non-existent permissions."""
    auth = AuthTestHelper(client, db_session)
    headers = await auth.get_auth_headers(group_name=UserGroupEnum.USER)

    stmt = select(MovieModel).limit(1)
    result = await db_session.execute(stmt)
    movie = result.scalars().first()
    assert movie is not None, "No movies found in the database to delete."

    movie_id = movie.id

    response = await client.delete(f"/admin/movies/{movie_id}/", headers=headers)
    assert response.status_code == 404, f"Expected status code 404, but got {response.status_code}"

    stmt_check = select(MovieModel).where(MovieModel.id == movie_id)
    result_check = await db_session.execute(stmt_check)
    deleted_movie = result_check.scalars().first()
    assert deleted_movie is not None, f"Movie with ID {movie_id} deleted."


@pytest.mark.asyncio
async def test_update_movie_success(client, db_session, seed_database):
    """
    Test the `/movies/{movie_id}/` endpoint for successfully updating a movie's details.
    """
    auth = AuthTestHelper(client, db_session)
    headers = await auth.get_auth_headers(group_name=UserGroupEnum.ADMIN)

    stmt = select(MovieModel).limit(1)
    result = await db_session.execute(stmt)
    movie = result.scalars().first()
    assert movie is not None, "No movies found in the database to update."

    movie_id = movie.id
    update_data = {
        "name": "Updated Movie Name",
        "year": 2000,
    }

    response = await client.patch(f"/admin/movies/{movie_id}/", json=update_data, headers=headers)
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"

    response_data = response.json()
    assert response_data["detail"] == "Movie updated successfully.", (
        f"Expected detail message: 'Movie updated successfully.', but got: {response_data['detail']}"
    )

    await db_session.rollback()

    stmt_check = select(MovieModel).where(MovieModel.id == movie_id)
    result_check = await db_session.execute(stmt_check)
    updated_movie = result_check.scalars().first()

    assert updated_movie.name == update_data["name"], "Movie name was not updated."
    assert updated_movie.year == update_data["year"], "Movie year was not updated."

@pytest.mark.asyncio
async def test_update_movie_not_permissions(client, db_session, seed_database):
    """
    Test the `/movies/{movie_id}/` endpoint for successfully updating a movie's details.
    """
    auth = AuthTestHelper(client, db_session)
    headers = await auth.get_auth_headers(group_name=UserGroupEnum.USER)

    stmt = select(MovieModel).limit(1)
    result = await db_session.execute(stmt)
    movie = result.scalars().first()
    assert movie is not None, "No movies found in the database to update."

    movie_id = movie.id
    update_data = {
        "name": "Updated Movie Name",
        "year": 1899,
    }

    response = await client.patch(f"/admin/movies/{movie_id}/", json=update_data, headers=headers)
    assert response.status_code == 404, f"Expected status code 404, but got {response.status_code}"

    await db_session.rollback()

    stmt_check = select(MovieModel).where(MovieModel.id == movie_id)
    result_check = await db_session.execute(stmt_check)
    updated_movie = result_check.scalars().first()

    assert updated_movie.name != update_data["name"], "Movie name was not updated."
    assert updated_movie.year != update_data["year"], "Movie year was not updated."


@pytest.mark.asyncio
async def test_update_movie_not_found(client, db_session, seed_database):
    """
    Test the `/movies/{movie_id}/` endpoint with a non-existent movie ID.
    """
    auth = AuthTestHelper(client, db_session)
    headers = await auth.get_auth_headers(group_name=UserGroupEnum.ADMIN)

    non_existent_id = 99999
    update_data = {
        "name": "Non-existent Movie",
        "year": 2005
    }

    response = await client.patch(f"/admin/movies/{non_existent_id}/", json=update_data, headers=headers)
    assert response.status_code == 404, f"Expected status code 404, but got {response.status_code}"

    response_data = response.json()
    expected_detail = "Movie not found."
    assert response_data["detail"] == expected_detail, (
        f"Expected detail message: {expected_detail}, but got: {response_data['detail']}"
    )

@pytest.mark.asyncio
async def test_change_group_for_user(client, db_session):
    auth = AuthTestHelper(client, db_session)
    headers = await auth.get_auth_headers(group_name=UserGroupEnum.ADMIN)

    await db_session.rollback()

    new_user = await auth.create_user(
        email="new_user_email@example.com",
        password="StroNGPassword@!!123",
        group_name=UserGroupEnum.USER,
    )

    data = {
        "email": "new_user_email@example.com",
        "role": UserRoleEnum.ADMIN,
    }

    response = await client.post("/admin/group_change/", json=data, headers=headers)
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"

    await db_session.refresh(new_user)

    stmt_check = select(UserModel).where(UserModel.id == new_user.id).options(
        selectinload(UserModel.group)
    )
    result_check = await db_session.execute(stmt_check)
    new_user_check = result_check.scalar_one_or_none()

    assert data["role"] == new_user_check.group.name, "User role was not updated."


@pytest.mark.asyncio
async def test_change_group_for_user_not_permissions(client, db_session):
    auth = AuthTestHelper(client, db_session)
    headers = await auth.get_auth_headers(group_name=UserGroupEnum.USER)

    new_user = await auth.create_user(
        email="new_user_email@example.com",
        password="StroNGPassword@!!123",
        group_name=UserGroupEnum.USER,
    )

    await db_session.rollback()

    data = {
        "email": "new_user_email@example.com",
        "role": UserRoleEnum.ADMIN,
    }
    await db_session.commit()

    response = await client.post("/admin/group_change/", json=data, headers=headers)
    assert response.status_code == 404, f"Expected status code 404, but got {response.status_code}"

    await db_session.refresh(new_user)

    stmt_check = select(UserModel).where(UserModel.id == new_user.id).options(
        selectinload(UserModel.group)
    )
    result_check = await db_session.execute(stmt_check)
    new_user_check = result_check.scalars().first()

    assert data["role"] != new_user_check.group, "User role updated."

@pytest.mark.asyncio
async def test_activate_account_using_admin(client, db_session):
    auth = AuthTestHelper(client, db_session)
    headers = await auth.get_auth_headers(group_name=UserGroupEnum.ADMIN)

    await db_session.rollback()

    new_user = await auth.create_user(
        email="new_user_email@example.com",
        password="StroNGPassword@!!123",
        group_name=UserGroupEnum.USER,
        is_active=False
    )

    data = {
        "email": "new_user_email@example.com",
    }

    response = await client.post("/admin/activate_account/", json=data, headers=headers)
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"

    await db_session.refresh(new_user)

    stmt_check = select(UserModel).where(UserModel.id == new_user.id)
    result_check = await db_session.execute(stmt_check)
    new_user_check = result_check.scalar_one_or_none()

    assert new_user_check.is_active == True, "The user was not activated by an admin."


@pytest.mark.asyncio
async def test_activate_account_using_user_not_permission(client, db_session):
    auth = AuthTestHelper(client, db_session)
    headers = await auth.get_auth_headers(group_name=UserGroupEnum.USER)

    await db_session.rollback()

    new_user = await auth.create_user(
        email="new_user_email@example.com",
        password="StroNGPassword@!!123",
        group_name=UserGroupEnum.USER,
        is_active=False
    )

    data = {
        "email": "new_user_email@example.com",
    }

    response = await client.post("/admin/activate_account/", json=data, headers=headers)
    assert response.status_code == 404, f"Expected status code 404, but got {response.status_code}"

    await db_session.refresh(new_user)

    stmt_check = select(UserModel).where(UserModel.id == new_user.id)
    result_check = await db_session.execute(stmt_check)
    new_user_check = result_check.scalar_one_or_none()

    assert new_user_check.is_active == False, "The user was activated by an user."
