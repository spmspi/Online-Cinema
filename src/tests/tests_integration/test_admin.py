import random
from decimal import Decimal

import pytest
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload

from database import UserGroupModel, UserGroupEnum, UserModel
from src.database import MovieModel, DirectorModel
from src.database import (
    GenreModel,
    StarModel,
    CertificationModel,
)

@pytest.mark.asyncio
async def test_create_movie_and_related_models(client, db_session):
    """
    Test that a new movie is created successfully and related models
    (genres, stars, certification, ) are created if they do not exist.
    """
    user_payload = {
        "email": "testuser@example.com",
        "password": "StrongPassword123!"
    }

    stmt = select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.ADMIN)
    result = await db_session.execute(stmt)
    user_group = result.scalars().first()
    assert user_group is not None, "Default user group should exist."

    user = UserModel.create(
        email=user_payload["email"],
        raw_password=user_payload["password"],
        group_id=user_group.id
    )
    user.is_active = True
    db_session.add(user)
    await db_session.commit()

    login_response = await client.post(
        "/login/",
        json={
            "email": user_payload["email"],
            "password": user_payload["password"],
        },
    )
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"

    login_data = login_response.json()
    access_token = login_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

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
    user_payload = {
        "email": "testuser@example.com",
        "password": "StrongPassword123!"
    }

    stmt = select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.ADMIN)
    result = await db_session.execute(stmt)
    user_group = result.scalars().first()
    assert user_group is not None, "Default user group should exist."

    user = UserModel.create(
        email=user_payload["email"],
        raw_password=user_payload["password"],
        group_id=user_group.id
    )
    user.is_active = True
    db_session.add(user)
    await db_session.commit()

    login_response = await client.post(
        "/login/",
        json={
            "email": user_payload["email"],
            "password": user_payload["password"],
        },
    )
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"

    login_data = login_response.json()
    access_token = login_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

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
