import random
from decimal import Decimal

import pytest
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload, selectinload

from src.database import MovieModel, UserModel
from src.database.models.cart import CartModel, CartItemModel
from src.database import UserGroupEnum
from src.tests.service_tests import AuthTestHelper


@pytest.mark.asyncio
async def test_add_movie_in_cart(client, db_session, seed_database, seed_cart_movies):
    auth = AuthTestHelper(client, db_session)
    headers = await auth.get_auth_headers(group_name=UserGroupEnum.USER)
    await seed_cart_movies(headers=headers, count=5)

    response = await client.get("/cart/", headers=headers)
    assert response.status_code == 200, "Expected status code 200, but got a different value"

    response_data = response.json()

    assert len(response_data["movies"]) == 5, "Expected 5 movies in the response, but got a different count"



@pytest.mark.asyncio
async def test_delete_movie_from_cart(client, db_session, seed_database, seed_cart_movies):
    auth = AuthTestHelper(client, db_session)
    headers = await auth.get_auth_headers(group_name=UserGroupEnum.USER)

    list_movie = await seed_cart_movies(headers=headers, count=5)

    response = await client.get("/cart/", headers=headers)
    assert response.status_code == 200, "Expected status code 200, but got a different value"

    response_data = response.json()

    assert len(response_data["movies"]) == 5, "Expected 5 movies in the response, but got a different count"

    response = await client.delete(f"/cart/{list_movie[0]}/", headers=headers)
    assert response.status_code == 200, "Expected status code 200, but got a different value"

    user = await auth.get_user()
    stmt_cart = select(UserModel).filter(UserModel.email == user.email).options(selectinload(UserModel.cart).selectinload(CartModel.cart_items).selectinload(CartItemModel.movie))
    result_cart = await db_session.execute(stmt_cart)
    user_cart = result_cart.scalars().one()

    assert len(user_cart.cart.cart_items) == 4, "Expected 4 movies in the response, but got a different count"

    expected_detail = {"message": "movie removed from cart"}
    assert response.json() == expected_detail, f"Expected {expected_detail}, got {response.json()}"


@pytest.mark.asyncio
async def test_clear_cart(client, db_session, seed_database, seed_cart_movies):
    auth = AuthTestHelper(client, db_session)
    headers = await auth.get_auth_headers(group_name=UserGroupEnum.USER)
    list_movie = await seed_cart_movies(headers=headers, count=5)

    response = await client.delete("/cart/", headers=headers)
    assert response.status_code == 200, "Expected status code 200, but got a different value"
    expected_detail = {"message": "item removed from cart"}
    assert response.json() == expected_detail, f"Expected {expected_detail}, got {response.json()}"

    user = await auth.get_user()
    stmt_cart = select(UserModel).filter(UserModel.email == user.email).options(
        selectinload(UserModel.cart).selectinload(CartModel.cart_items).selectinload(CartItemModel.movie))

    result_cart = await db_session.execute(stmt_cart)
    user_cart = result_cart.scalars().one()

    assert len(user_cart.cart.cart_items) == 0, "Expected 0 movies in the response, but got a different count"

@pytest.mark.asyncio
async def test_exceptions_cart(client, db_session, seed_cart_movies, seed_database):
    auth = AuthTestHelper(client, db_session)
    headers = await auth.get_auth_headers(group_name=UserGroupEnum.USER)

    movie_id = 1000

    response = await client.post(f"/cart/{movie_id}/", headers=headers)
    assert response.status_code == 404, (
        f"Expected status code 404 when adding movie {movie_id}, got {response.status_code}"
    )
    expected_detail = {"detail": "Movie not found."}
    assert response.json() == expected_detail, f"Expected {expected_detail}, got {response.json()}"

    response = await client.delete(f"/cart/{movie_id}/", headers=headers)
    assert response.status_code == 404, (
        f"Expected status code 404 when adding movie {movie_id}, got {response.status_code}"
    )
    expected_detail = {"detail": "Movie not found."}
    assert response.json() == expected_detail, f"Expected {expected_detail}, got {response.json()}"

    conflict_movie_id = 1

    response_one = await client.post(f"/cart/{conflict_movie_id}/", headers=headers)
    assert response_one.status_code == 200, "Expected status code 200, but got a different value"
    response_two = await client.post(f"/cart/{conflict_movie_id}/", headers=headers)
    assert response_two.status_code == 409, (
        f"Expected status code 409 when adding movie {movie_id}, got {response_two.status_code}"
    )

    expected_detail = {"detail": "This movie is already in the cart."}
    assert response_two.json() == expected_detail, f"Expected {expected_detail}, got {response_two.json()}"

@pytest.mark.asyncio
async def test_clear_cart_for_empty_cart(client, db_session, seed_database, seed_cart_movies):
    auth = AuthTestHelper(client, db_session)
    headers = await auth.get_auth_headers(group_name=UserGroupEnum.USER)

    response = await client.delete("/cart/", headers=headers)
    assert response.status_code == 404, "Expected status code 404, but got a different value"

    expected_detail = {"detail": "The cart is empty"}
    assert response.json() == expected_detail, f"Expected {expected_detail}, got {response.json()}"

