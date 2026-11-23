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
from tests.service_tests import AuthTestHelper


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


@pytest.mark.asyncio
async def test_movies_sorted_by_items(client, db_session, seed_database):
    """
    Test that the film is correctly filtered by attributes such as price, year, and film rating.
    """
    response = await client.get("/movies/?page=1&limit=10", params={"sort_by": "price_asc"})
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"
    response_data = response.json()

    stmt = select(MovieModel).order_by(MovieModel.price.asc()).limit(10)
    result = await db_session.execute(stmt)
    expected_movies = result.scalars().all()

    expected_movie_ids = [movie.id for movie in expected_movies]
    returned_movie_ids = [movie["id"] for movie in response_data["movies"]]

    assert returned_movie_ids == expected_movie_ids, (
        f"Movies are not sorted by `Price ASC` in descending order. "
        f"Expected: {expected_movie_ids}, but got: {returned_movie_ids}"
    )


    response = await client.get("/movies/?page=1&limit=10", params={"sort_by": "price_desc"})
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"
    response_data = response.json()

    stmt = select(MovieModel).order_by(MovieModel.price.desc()).limit(10)
    result = await db_session.execute(stmt)
    expected_movies = result.scalars().all()

    expected_movie_ids = [movie.id for movie in expected_movies]
    returned_movie_ids = [movie["id"] for movie in response_data["movies"]]

    assert returned_movie_ids == expected_movie_ids, (
        f"Movies are not sorted by `Price DESC` in descending order. "
        f"Expected: {expected_movie_ids}, but got: {returned_movie_ids}"
    )

    response = await client.get("/movies/?page=1&limit=10", params={"sort_by": "price_desc"})
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"
    response_data = response.json()

    stmt = select(MovieModel).order_by(MovieModel.price.desc()).limit(10)
    result = await db_session.execute(stmt)
    expected_movies = result.scalars().all()

    expected_movie_ids = [movie.id for movie in expected_movies]
    returned_movie_ids = [movie["id"] for movie in response_data["movies"]]

    assert returned_movie_ids == expected_movie_ids, (
        f"Movies are not sorted by `Price DESC` in descending order. "
        f"Expected: {expected_movie_ids}, but got: {returned_movie_ids}"
    )

    response = await client.get("/movies/?page=1&limit=10", params={"sort_by": "year_asc"})
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"
    response_data = response.json()

    stmt = select(MovieModel).order_by(MovieModel.year.asc()).limit(10)
    result = await db_session.execute(stmt)
    expected_movies = result.scalars().all()

    expected_movie_ids = [movie.id for movie in expected_movies]
    returned_movie_ids = [movie["id"] for movie in response_data["movies"]]

    assert returned_movie_ids == expected_movie_ids, (
        f"Movies are not sorted by `YEAR ASC` in descending order. "
        f"Expected: {expected_movie_ids}, but got: {returned_movie_ids}"
    )

    response = await client.get("/movies/?page=1&limit=10", params={"sort_by": "year_desc"})
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"
    response_data = response.json()

    stmt = select(MovieModel).order_by(MovieModel.year.desc()).limit(10)
    result = await db_session.execute(stmt)
    expected_movies = result.scalars().all()

    expected_movie_ids = [movie.id for movie in expected_movies]
    returned_movie_ids = [movie["id"] for movie in response_data["movies"]]

    assert returned_movie_ids == expected_movie_ids, (
        f"Movies are not sorted by `YEAR DESC` in descending order. "
        f"Expected: {expected_movie_ids}, but got: {returned_movie_ids}"
    )

    response = await client.get("/movies/?page=1&limit=10", params={"sort_by": "meta_score_desc"})
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"
    response_data = response.json()

    stmt = select(MovieModel).order_by(MovieModel.meta_score.desc()).limit(10)
    result = await db_session.execute(stmt)
    expected_movies = result.scalars().all()

    expected_movie_ids = [movie.id for movie in expected_movies]
    returned_movie_ids = [movie["id"] for movie in response_data["movies"]]

    assert returned_movie_ids == expected_movie_ids, (
        f"Movies are not sorted by `Meta Score DESC` in descending order. "
        f"Expected: {expected_movie_ids}, but got: {returned_movie_ids}"
    )

    response = await client.get("/movies/?page=1&limit=10", params={"sort_by": "meta_score_asc"})
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"
    response_data = response.json()

    stmt = select(MovieModel).order_by(MovieModel.meta_score.asc()).limit(10)
    result = await db_session.execute(stmt)
    expected_movies = result.scalars().all()

    expected_movie_ids = [movie.id for movie in expected_movies]
    returned_movie_ids = [movie["id"] for movie in response_data["movies"]]

    assert returned_movie_ids == expected_movie_ids, (
        f"Movies are not sorted by `Meta Score ASC` in descending order. "
        f"Expected: {expected_movie_ids}, but got: {returned_movie_ids}"
    )




@pytest.mark.asyncio
async def test_movies_fields_match_schema(client, db_session, seed_database):
    """
    Test that each movie in the response matches the fields defined in `MovieListItemSchema`.
    """
    response = await client.get("/movies/?page=1&per_page=10")

    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"

    response_data = response.json()

    assert "movies" in response_data, "Response missing 'movies' field."

    expected_fields = {"id", "name", "year", "meta_score", "description"}

    for movie in response_data["movies"]:
        assert set(movie.keys()) == expected_fields, (
            f"Movie fields do not match schema. "
            f"Expected: {expected_fields}, but got: {set(movie.keys())}"
        )


@pytest.mark.asyncio
async def test_get_movie_by_id_not_found(client):
    """
    Test that the `/movies/{movie_id}` endpoint returns a 404 error
    when a movie with the given ID does not exist.
    """
    movie_id = 1

    response = await client.get(f"/movies/{movie_id}/")
    assert response.status_code == 404, f"Expected status code 404, but got {response.status_code}"

    response_data = response.json()
    assert response_data == {"detail": "Movie with the given ID was not found."}, (
        f"Expected error message not found. Got: {response_data}"
    )


@pytest.mark.asyncio
async def test_get_movie_by_id_valid(client, db_session, seed_database):
    """
    Test that the `/movies/{movie_id}` endpoint returns the correct movie details
    when a valid movie ID is provided.

    Verifies the following:
    - The movie exists in the database.
    - The response status code is 200.
    - The movie's `id` and `name` in the response match the expected values from the database.
    """
    stmt_min = select(MovieModel.id).order_by(MovieModel.id.asc()).limit(1)
    result_min = await db_session.execute(stmt_min)
    min_id = result_min.scalars().first()

    stmt_max = select(MovieModel.id).order_by(MovieModel.id.desc()).limit(1)
    result_max = await db_session.execute(stmt_max)
    max_id = result_max.scalars().first()

    random_id = random.randint(min_id, max_id)

    stmt_movie = select(MovieModel).where(MovieModel.id == random_id)
    result_movie = await db_session.execute(stmt_movie)
    expected_movie = result_movie.scalars().first()
    assert expected_movie is not None, "Movie not found in database."

    response = await client.get(f"/movies/{random_id}/")
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"

    response_data = response.json()

    assert response_data["id"] == expected_movie.id, "Returned ID does not match the requested ID."
    assert response_data["name"] == expected_movie.name, "Returned name does not match the expected name."



@pytest.mark.asyncio
async def test_get_movie_by_id_fields_match_database(client, db_session, seed_database):
    """
    Test that the `/movies/{movie_id}` endpoint returns all fields matching the database data.
    """
    stmt = (
        select(MovieModel)
        .options(
            joinedload(MovieModel.comments),
            joinedload(MovieModel.certification),
            joinedload(MovieModel.genres),
            joinedload(MovieModel.stars),
            joinedload(MovieModel.directors),
        )
        .limit(1)
    )
    result = await db_session.execute(stmt)
    random_movie = result.scalars().first()
    assert random_movie is not None, "No movies found in the database."

    response = await client.get(f"/movies/{random_movie.id}/")
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"

    response_data = response.json()

    assert response_data["id"] == random_movie.id, "ID does not match."
    assert response_data["year"] == random_movie.year, "Date does not match."
    assert response_data["time"] == random_movie.time, "Score does not match."
    assert response_data["imdb"] == random_movie.imdb, "imdb does not match."
    assert response_data["votes"] == random_movie.votes, "votes does not match."
    assert response_data["meta_score"] == random_movie.meta_score, "meta score does not match."
    assert response_data["gross"] == random_movie.gross, "gross does not match."
    assert response_data["description"] == random_movie.description, "description does not match."
    assert response_data["price"] == float(random_movie.price), "price does not match."
    assert response_data["likes_count"] == random_movie.likes_count, "likes_count does not match."
    assert response_data["dislikes_count"] == random_movie.dislikes_count, "dislikes_count does not match."

    assert response_data["certification"]["id"] == random_movie.certification.id, "certification ID does not match."
    assert response_data["certification"]["name"] == random_movie.certification.name, "certification name does not match."

    actual_genres = sorted(response_data["genres"], key=lambda x: x["id"])
    expected_genres = sorted(
        [{"id": genre.id, "name": genre.name} for genre in random_movie.genres],
        key=lambda x: x["id"]
    )
    assert actual_genres == expected_genres, "Genres do not match."

    actual_stars = sorted(response_data["stars"], key=lambda x: x["id"])
    expected_actors = sorted(
        [{"id": star.id, "name": star.name} for star in random_movie.stars],
        key=lambda x: x["id"]
    )

    assert actual_stars == expected_actors, "Genres do not match."

    actual_directors = sorted(response_data["directors"], key=lambda x: x["id"])
    expected_directors = sorted(
        [{"id": director.id, "name": director.name} for director in random_movie.directors],
        key=lambda x: x["id"]
    )

    assert actual_directors == expected_directors, "Directors do not match."


@pytest.mark.asyncio
async def test_post_score_movie(client, db_session, seed_database):

    auth = AuthTestHelper(client, db_session)
    headers = await auth.get_auth_headers(group_name=UserGroupEnum.USER)

    stmt = select(MovieModel)
    result_min = await db_session.execute(stmt)
    movie = result_min.scalars().first()
    old_score = movie.meta_score
    data = {
        "score": 10.0
    }
    assert movie is not None, "Movie not found in database."

    response = await client.post(f"/movies/{movie.id}/rating/", json=data, headers=headers)
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"

    await db_session.refresh(movie)
    new_score = movie.meta_score
    assert old_score != new_score, "Score should not be updated."

    data_negative_score = {
        "score": -10.0
    }

    response = await client.post(f"/movies/{movie.id}/rating/", json=data_negative_score, headers=headers)
    assert response.status_code == 422, f"Expected status code 422, but got {response.status_code}"

    await db_session.refresh(movie)
    new_score_negative = movie.meta_score

    assert new_score == new_score_negative, "Score should updated using negative score."

    data_big_score = {
        "score": 15.0
    }
    response = await client.post(f"/movies/{movie.id}/rating/", json=data_big_score, headers=headers)
    assert response.status_code == 422, f"Expected status code 422, but got {response.status_code}"

    await db_session.refresh(movie)
    new_score_big_positive = movie.meta_score

    assert new_score == new_score_big_positive, "Score should updated using big positive score."

    new_score_again = {
        "score": 6.0
    }
    response = await client.post(f"/movies/{movie.id}/rating/", json=new_score_again, headers=headers)
    assert response.status_code == 400, f"Expected status code 400, but got {response.status_code}"


