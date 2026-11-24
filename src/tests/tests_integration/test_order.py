import random
from decimal import Decimal

import pytest
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload, selectinload

from src.database.models.order import OrdersModel
from src.database.models.order import StatusOrderEnum
from src.database.models.payments import StatusPaymentsEnum
from src.database import MovieModel, UserModel
from src.database.models.cart import CartModel, CartItemModel
from src.database import UserGroupEnum
from src.tests.service_tests import AuthTestHelper


@pytest.mark.asyncio
async def test_create_order(client, db_session, seed_database, seed_cart_movies):
    auth = AuthTestHelper(client, db_session)
    headers = await auth.get_auth_headers(group_name=UserGroupEnum.USER)
    await seed_cart_movies(headers=headers, count=5)

    stmt = select(MovieModel).limit(5)
    res = await db_session.execute(stmt)
    movie_list = res.scalars().all()
    total_price = 0
    for movie in movie_list:
        total_price += movie.price

    response = await client.get("/cart/", headers=headers)
    assert response.status_code == 200, "Expected status code 200, but got a different value"

    response_data = response.json()

    assert len(response_data["movies"]) == 5, "Expected 5 movies in the response, but got a different count"

    response = await client.post("/order/", headers=headers)

    assert response.status_code == 201, "Expected status code 201, but got a different value"

    user = await auth.get_user()
    stmt_cart = select(UserModel).filter(UserModel.email == user.email).options(
        selectinload(UserModel.cart).selectinload(CartModel.cart_items).selectinload(CartItemModel.movie))

    result_cart = await db_session.execute(stmt_cart)
    user_cart = result_cart.scalars().one()

    assert len(user_cart.cart.cart_items) == 0, "After an order is created, the cart should be cleared."

    response_data = response.json()

    assert response_data["id"] is not None
    assert response_data["user_id"] is not None
    assert response_data["created_at"] is not None
    assert response_data["status"] == StatusOrderEnum.PENDING.value
    assert Decimal(response_data["total_amount"]) == total_price

@pytest.mark.asyncio
async def test_get_order(client, db_session, seed_database, seed_cart_movies):
    auth = AuthTestHelper(client, db_session)
    headers = await auth.get_auth_headers(group_name=UserGroupEnum.USER)
    await seed_cart_movies(headers=headers, count=5)

    stmt = select(MovieModel).limit(5)
    res = await db_session.execute(stmt)
    movie_list = res.scalars().all()
    total_price = 0
    for movie in movie_list:
        total_price += movie.price

    response = await client.get("/cart/", headers=headers)
    assert response.status_code == 200, "Expected status code 200, but got a different value"

    response_data = response.json()

    assert len(response_data["movies"]) == 5, "Expected 5 movies in the response, but got a different count"

    response = await client.post("/order/", headers=headers)

    assert response.status_code == 201, "Expected status code 201, but got a different value"

    response_data = response.json()

    assert response_data["id"] is not None
    assert response_data["user_id"] is not None
    assert response_data["created_at"] is not None
    assert response_data["status"] == StatusOrderEnum.PENDING.value
    assert Decimal(response_data["total_amount"]) == total_price

    response = await client.get("/order/", headers=headers)
    assert response.status_code == 200, "Expected status code 200, but got a different value"

    response_data = response.json()

    assert response_data["user_id"] is not None
    assert response_data["orders"] is not None


@pytest.mark.asyncio
async def test_create_the_same_order(client, db_session, seed_database, seed_cart_movies):
    auth = AuthTestHelper(client, db_session)
    headers = await auth.get_auth_headers(group_name=UserGroupEnum.USER)
    await seed_cart_movies(headers=headers, count=5)

    response = await client.get("/cart/", headers=headers)
    assert response.status_code == 200, "Expected status code 200, but got a different value"

    response = await client.post("/order/", headers=headers)
    assert response.status_code == 201, "Expected status code 201, but got a different value"

    await seed_cart_movies(headers=headers, count=5)
    response = await client.post("/order/", headers=headers)
    assert response.status_code == 404, "Expected status code 404, but got a different value"

    expected_detail = {"detail": "You have unpaid orders."}
    assert response.json() == expected_detail, f"Expected {expected_detail}, got {response.json()}"


@pytest.mark.asyncio
async def test_cart_for_paid_movie(client, db_session, seed_database, seed_cart_movies):
    auth = AuthTestHelper(client, db_session)
    headers = await auth.get_auth_headers(group_name=UserGroupEnum.USER)
    await seed_cart_movies(headers=headers, count=5)

    response = await client.post("/order/", headers=headers)
    assert response.status_code == 201, "Expected status code 201, but got a different value"

    stmt = select(OrdersModel)
    result = await db_session.execute(stmt)
    order = result.scalars().first()
    order.status = StatusOrderEnum.PAID
    await db_session.commit()

    movie_id = 1

    response = await client.post(f"/cart/{movie_id}/", headers=headers)
    assert response.status_code == 409, "Expected status code 409, but got a different value"

    expected_detail = {"detail": "This film has already been purchased."}
    assert response.json() == expected_detail, f"Expected {expected_detail}, got {response.json()}"

@pytest.mark.asyncio
async def test_create_order_clear_cart(client, db_session, seed_database):
    auth = AuthTestHelper(client, db_session)
    headers = await auth.get_auth_headers(group_name=UserGroupEnum.USER)

    response = await client.post("/order/", headers=headers)
    assert response.status_code == 404, "Expected status code 404, but got a different value"


@pytest.mark.asyncio
async def test_update_price_for_movie_and_create_order(client, db_session, seed_database, seed_cart_movies):
    auth = AuthTestHelper(client, db_session)
    headers = await auth.get_auth_headers(group_name=UserGroupEnum.USER)
    await seed_cart_movies(headers=headers, count=5)

    stmt = select(MovieModel).limit(5)
    res = await db_session.execute(stmt)
    movie_list = res.scalars().all()
    old_price = 0
    for movie in movie_list:
        old_price += movie.price

    response = await client.get("/cart/", headers=headers)
    assert response.status_code == 200, "Expected status code 200, but got a different value"

    stmt = select(MovieModel).where(MovieModel.id == 1)
    result = await db_session.execute(stmt)
    movie = result.scalar_one_or_none()
    movie.price = Decimal(10000)
    await db_session.commit()
    await db_session.refresh(movie)

    stmt = select(MovieModel).limit(5)
    res = await db_session.execute(stmt)
    new_movie_list = res.scalars().all()

    new_price = 0
    for movie in new_movie_list:
        new_price += movie.price

    response = await client.post("/order/", headers=headers)
    assert response.status_code == 201, "Expected status code 201, but got a different value"
    response_data = response.json()
    assert response_data["id"] is not None
    assert response_data["user_id"] is not None
    assert response_data["created_at"] is not None
    assert response_data["status"] == StatusOrderEnum.PENDING.value
    assert Decimal(response_data["total_amount"]) == new_price
    assert new_price != old_price


@pytest.mark.asyncio
async def test_cancel_order(client, db_session, seed_database, seed_cart_movies):
    auth = AuthTestHelper(client, db_session)
    headers = await auth.get_auth_headers(group_name=UserGroupEnum.USER)
    await seed_cart_movies(headers=headers, count=5)

    response = await client.post("/order/", headers=headers)
    assert response.status_code == 201, "Expected status code 201, but got a different value"

    order_id = 1

    response = await client.patch(f"/order/{order_id}/cancel/", headers=headers)
    assert response.status_code == 200, "Expected status code 200, but got a different value"
    expected_detail = {"message": "order canceled"}
    assert response.json() == expected_detail, f"Expected {expected_detail}, got {response.json()}"
    stmt = select(OrdersModel).where(OrdersModel.id == order_id)
    res = await db_session.execute(stmt)
    order = res.scalar_one_or_none()
    assert order.status == StatusOrderEnum.CANCELED.value


@pytest.mark.asyncio
async def test_cancel_order_not_found(client, db_session, seed_database, seed_cart_movies):
    auth = AuthTestHelper(client, db_session)
    headers = await auth.get_auth_headers(group_name=UserGroupEnum.USER)

    order_id = 1

    response = await client.patch(f"/order/{order_id}/cancel/", headers=headers)
    assert response.status_code == 404, "Expected status code 404, but got a different value"

    expected_detail = {"detail": "Order not found."}
    assert response.json() == expected_detail, f"Expected {expected_detail}, got {response.json()}"

@pytest.mark.asyncio
async def test_detail_order_not_found(client, db_session, seed_database, seed_cart_movies):
    auth = AuthTestHelper(client, db_session)
    headers = await auth.get_auth_headers(group_name=UserGroupEnum.USER)

    order_id = 1

    response = await client.get(f"/order/{order_id}/", headers=headers)
    assert response.status_code == 404, "Expected status code 404, but got a different value"
    expected_detail = {"detail": "Order not found."}
    assert response.json() == expected_detail, f"Expected {expected_detail}, got {response.json()}"

@pytest.mark.asyncio
async def test_detail_order(client, db_session, seed_database, seed_cart_movies):
    auth = AuthTestHelper(client, db_session)
    headers = await auth.get_auth_headers(group_name=UserGroupEnum.USER)
    await seed_cart_movies(headers=headers, count=5)

    response = await client.post("/order/", headers=headers)
    assert response.status_code == 201, "Expected status code 201, but got a different value"

    order_id = 1
    response = await client.get(f"/order/{order_id}/", headers=headers)
    assert response.status_code == 200, "Expected status code 200, but got a different value"

    response_data = response.json()

    assert response_data["id"] is not None
    assert response_data["user_id"] is not None
    assert response_data["created_at"] is not None
    assert len(response_data["movies"]) == 5, (
        f"was added to the order 5 movies, but got {len(response_data['movies'])}"
    )

@pytest.mark.asyncio
async def test_get_my_orders(client, db_session, seed_database, seed_cart_movies):
    auth = AuthTestHelper(client, db_session)
    headers = await auth.get_auth_headers(group_name=UserGroupEnum.USER)
    await seed_cart_movies(headers=headers, count=5)

    response = await client.post("/order/", headers=headers)
    assert response.status_code == 201, "Expected status code 201, but got a different value"

    order_id = 1
    response = await client.patch(f"/order/{order_id}/cancel/", headers=headers)
    assert response.status_code == 200, "Expected status code 200, but got a different value"

    await seed_cart_movies(headers=headers, count=5)

    response = await client.post("/order/", headers=headers)
    assert response.status_code == 201, "Expected status code 201, but got a different value"

    response = await client.get("/order/", headers=headers)
    assert response.status_code == 200, "Expected status code 200, but got a different value"

    response_data = response.json()

    assert response_data["user_id"] == 1
    assert len(response_data["orders"]) == 2, (
        f"2 orders were created, but via a GET request but got {len(response_data['orders'])}"
    )


@pytest.mark.asyncio
async def test_create_order_for_empty_cart(client, db_session, seed_database, seed_cart_movies):
    auth = AuthTestHelper(client, db_session)
    headers = await auth.get_auth_headers(group_name=UserGroupEnum.USER)

    response = await client.post("/order/", headers=headers)
    assert response.status_code == 404, "Expected status code 404, but got a different value"

    expected_detail = {"detail": "The cart is empty"}
    assert response.json() == expected_detail, f"Expected {expected_detail}, got {response.json()}"















