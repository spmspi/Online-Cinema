import random

import pytest
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload

from src.database import MovieModel, DirectorModel
from src.database import (
    GenreModel,
    StarModel,
    CertificationModel,
)


@pytest.mark.asyncio
async def test_get_movies_empty_database(client):
    """
    Test that the `/movies/` endpoint returns a 404 error when the database is empty.
    """
    response = await client.get("/movies/")
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"

    expected_detail = {"detail": "No movies found."}
    assert response.json() == expected_detail, f"Expected {expected_detail}, got {response.json()}"



@pytest.mark.asyncio
async def test_get_movies_default_parameters(client, seed_database):
    """
    Test the `/movies/` endpoint with default pagination parameters.
    """
    response = await client.get("/movies/")
    assert response.status_code == 200, "Expected status code 200, but got a different value"

    response_data = response.json()

    assert len(response_data["movies"]) == 10, "Expected 10 movies in the response, but got a different count"

    assert response_data["total_pages"] > 0, "Expected total_pages > 0, but got a non-positive value"
    assert response_data["total_items"] > 0, "Expected total_items > 0, but got a non-positive value"

    assert response_data["prev_page"] is None, "Expected prev_page to be None on the first page, but got a value"

    if response_data["total_pages"] > 1:
        assert response_data["next_page"] is not None, (
            "Expected next_page to be present when total_pages > 1, but got None"
        )

@pytest.mark.asyncio
async def test_get_movies_with_custom_parameters(client, seed_database):
    """
    Test the `/movies/` endpoint with custom pagination parameters.
    """
    page = 2
    limit = 5

    response = await client.get(f"/movies/?page={page}&limit={limit}")

    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"

    response_data = response.json()

    assert len(response_data["movies"]) == limit, (
        f"Expected {limit} movies in the response, but got {len(response_data['movies'])}"
    )

    assert response_data["total_pages"] > 0, "Expected total_pages > 0, but got a non-positive value"
    assert response_data["total_items"] > 0, "Expected total_items > 0, but got a non-positive value"

    if page > 1:
        assert response_data["prev_page"] == f"/movies/?page={page - 1}&limit={limit}", (
            f"Expected prev_page to be '/movies/?page={page - 1}&limit={limit}', "
            f"but got {response_data['prev_page']}"
        )

    if page < response_data["total_pages"]:
        assert response_data["next_page"] == f"/movies/?page={page + 1}&limit={limit}", (
            f"Expected next_page to be '/movies/?page={page + 1}&limit={limit}', "
            f"but got {response_data['next_page']}"
        )
    else:
        assert response_data["next_page"] is None, "Expected next_page to be None on the last page, but got a value"


@pytest.mark.asyncio
async def test_per_page_maximum_allowed_value(client, seed_database):
    """
    Test the `/movies/` endpoint with the maximum allowed `per_page` value.
    """
    response = await client.get("/movies/?page=1&limit=20")

    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"

    response_data = response.json()

    assert "movies" in response_data, "Response missing 'movies' field."
    assert len(response_data["movies"]) <= 20, (
        f"Expected at most 20 movies, but got {len(response_data['movies'])}"
    )

@pytest.mark.asyncio
async def test_page_exceeds_maximum(client, db_session, seed_database):
    """
    Test the `/movies/` endpoint with a page number that exceeds the maximum.
    """
    limit = 10

    count_stmt = select(func.count(MovieModel.id))
    result = await db_session.execute(count_stmt)
    total_movies = result.scalar_one()

    max_page = (total_movies + limit - 1) // limit

    response = await client.get(f"/movies/?page={max_page + 1}&limit={limit}")

    assert response.status_code == 404, f"Expected status code 404, but got {response.status_code}"
    response_data = response.json()

    assert "detail" in response_data, "Response missing 'detail' field."



@pytest.mark.asyncio
async def test_movies_sorted_by_id_desc(client, db_session, seed_database):
    """
    Test that movies are returned sorted by `id` in descending order
    and match the expected data from the database.
    """
    response = await client.get("/movies/?page=1&limit=10")

    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"

    response_data = response.json()

    stmt = select(MovieModel).order_by(MovieModel.id.desc()).limit(10)
    result = await db_session.execute(stmt)
    expected_movies = result.scalars().all()

    expected_movie_ids = [movie.id for movie in expected_movies]
    returned_movie_ids = [movie["id"] for movie in response_data["movies"]]

    assert returned_movie_ids == expected_movie_ids, (
        f"Movies are not sorted by `id` in descending order. "
        f"Expected: {expected_movie_ids}, but got: {returned_movie_ids}"
    )



@pytest.mark.asyncio
async def test_movies_filter_dy_name(client, db_session, seed_database):
    """
    testing search by movie title
    """
    response = await client.get("/movies/", params={"search": "Secret"})

    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"

    response_data = response.json()

    returned_movie_names = [movie["name"] for movie in response_data["movies"]]

    assert len(returned_movie_names) > 0, "Expected at least one movie matching 'Secret'"

    assert all("secret" in name.lower() for name in returned_movie_names), f"Some returned movies do not contain 'Secret': {returned_movie_names}"


@pytest.mark.asyncio
async def test_movies_filter_dy_star_name(client, db_session, seed_database):
    """
    testing search by star in movie
    """
    response = await client.get("/movies/", params={"search": "Leonardo DiCaprio"})

    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"

    response_data = response.json()

    returned_movie_ids = [movie["id"] for movie in response_data["movies"]]

    assert len(returned_movie_ids) > 0, "Expected at least one movie matching 'Leonardo DiCaprio'"

    stmt = select(MovieModel.id).join(MovieModel.stars).where(StarModel.name.ilike("Leonardo DiCaprio")).order_by(*MovieModel.default_order_by()).limit(10)
    result = await db_session.execute(stmt)
    search_results = result.scalars().all()

    list_ids = [movie for movie in search_results]

    assert list_ids == returned_movie_ids, (
        f"Filter by actor 'Leonardo DiCaprio' did not work, expected: {list_ids}"
        f"Received response: {returned_movie_ids}"
    )

    response = await client.get("/movies/", params={"search": "DiCap"})

    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"

    response_data = response.json()

    returned_movie_ids = [movie["id"] for movie in response_data["movies"]]

    assert len(returned_movie_ids) > 0, "Expected at least one movie matching 'DiCap'"

    assert list_ids == returned_movie_ids, (
        f"Filter by actor 'DiCap' did not work, expected: {list_ids}"
        f"Received response: {returned_movie_ids}"
    )


@pytest.mark.asyncio
async def test_movies_filter_dy_director_name(client, db_session, seed_database):
    """
    testing search by director in movie
    """
    response = await client.get("/movies/", params={"search": "Quentin Tarantino"})

    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"

    response_data = response.json()

    returned_movie_ids = [movie["id"] for movie in response_data["movies"]]

    assert len(returned_movie_ids) > 0, "Expected at least one movie matching 'Quentin Tarantino'"

    stmt = select(MovieModel.id).join(MovieModel.directors).where(DirectorModel.name.ilike("Quentin Tarantino")).order_by(*MovieModel.default_order_by()).limit(10)
    result = await db_session.execute(stmt)
    search_results = result.scalars().all()

    list_ids = [movie for movie in search_results]

    assert list_ids == returned_movie_ids, (
        f"Filter by director 'Quentin Tarantino' did not work, expected: {list_ids}"
        f"Received response: {returned_movie_ids}"
    )

    response = await client.get("/movies/", params={"search": "taran"})

    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"

    response_data = response.json()

    returned_movie_ids = [movie["id"] for movie in response_data["movies"]]

    assert len(returned_movie_ids) > 0, "Expected at least one movie matching 'taran'"


    assert list_ids == returned_movie_ids, (
        f"Filter by director 'taran' did not work, expected: {list_ids}"
        f"Received response: {returned_movie_ids}"
    )