from sqlalchemy import select

import pytest

from src.database.models.comments import CommentModel
from src.database import UserGroupEnum
from src.tests.service_tests import AuthTestHelper


@pytest.mark.asyncio
async def test_add_comment_for_movie(client, db_session, seed_database):
    auth = AuthTestHelper(client, db_session)
    headers = await auth.get_auth_headers(group_name=UserGroupEnum.USER)
    movie_id = 1
    data = {
        "text": "test comment for movie",
    }

    response = await client.post(f"/comment/{movie_id}/", headers=headers, json=data)
    assert response.status_code == 201, "Expected status code 201, but got a different value"

    response_data = response.json()

    assert response_data["id"] is not None
    assert response_data["text"] == data["text"]
    assert response_data["movie_id"] == movie_id
    assert response_data["user_id"] is not None


@pytest.mark.asyncio
async def test_get_comment(client, db_session, seed_database):
    auth = AuthTestHelper(client, db_session)
    headers = await auth.get_auth_headers(group_name=UserGroupEnum.USER)
    movie_id = 1
    data = {
       "text": "test comment for movie",
    }
    for _ in range(30):
        response = await client.post(f"/comment/{movie_id}/", headers=headers, json=data)
        assert response.status_code == 201, "Expected status code 201, but got a different value"

    response = await client.get(f"/comments/{movie_id}/", headers=headers)
    assert response.status_code == 200, "Expected status code 200, but got a different value"

    response_data = response.json()

    assert len(response_data["comments"]) == 10, "Expected 10 comments in the response, but got a different count"

    assert response_data["total_pages"] > 0, "Expected total_pages > 0, but got a non-positive value"
    assert response_data["total_items"] > 0, "Expected total_items > 0, but got a non-positive value"

    assert response_data["prev_page"] is None, "Expected prev_page to be None on the first page, but got a value"

    if response_data["total_pages"] > 1:
        assert response_data["next_page"] is not None, (
            "Expected next_page to be present when total_pages > 1, but got None"
        )

@pytest.mark.asyncio
async def test_add_sub_comment(client, db_session, seed_database):
    auth = AuthTestHelper(client, db_session)
    headers = await auth.get_auth_headers(group_name=UserGroupEnum.USER)

    movie_id = 1
    data = {
        "text": "test comment for movie",
    }

    response = await client.post(f"/comment/{movie_id}/", headers=headers, json=data)
    assert response.status_code == 201, "Expected status code 201, but got a different value"

    comment_id = 1
    data = {
        "text": "test sub comment for comment",
    }
    response = await client.post(f"/movie_comments/{comment_id}/", headers=headers, json=data)
    assert response.status_code == 201, "Expected status code 201, but got a different value"


@pytest.mark.asyncio
async def test_get_sub_comment(client, db_session, seed_database):
    auth = AuthTestHelper(client, db_session)
    headers = await auth.get_auth_headers(group_name=UserGroupEnum.USER)

    movie_id = 1
    data_comment = {
        "text": "test comment for movie",
    }

    response = await client.post(f"/comment/{movie_id}/", headers=headers, json=data_comment)
    assert response.status_code == 201, "Expected status code 201, but got a different value"

    data_sub_comment = {
        "text": "test sub comment for comment",
    }

    comment_id = 1

    for _ in range(30):
        response = await client.post(f"/movie_comments/{comment_id}/", headers=headers, json=data_sub_comment)
        assert response.status_code == 201, "Expected status code 201, but got a different value"

    response = await client.get(f"/movie_comments/{comment_id}/", headers=headers)
    assert response.status_code == 200, "Expected status code 200, but got a different value"

    response_data = response.json()

    assert len(response_data["comments"]) == 10, "Expected 10 sub comments in the response, but got a different count"

    assert response_data["total_pages"] > 0, "Expected total_pages > 0, but got a non-positive value"
    assert response_data["total_items"] > 0, "Expected total_items > 0, but got a non-positive value"

    assert response_data["prev_page"] is None, "Expected prev_page to be None on the first page, but got a value"

    if response_data["total_pages"] > 1:
        assert response_data["next_page"] is not None, (
            "Expected next_page to be present when total_pages > 1, but got None"
        )

@pytest.mark.asyncio
async def test_add_sub_comment_in_not_found_parent_comment(client, db_session, seed_database):
    auth = AuthTestHelper(client, db_session)
    headers = await auth.get_auth_headers(group_name=UserGroupEnum.USER)

    comment_id = 1
    data = {
        "text": "test sub comment for comment",
    }
    response = await client.post(f"/movie_comments/{comment_id}/", headers=headers, json=data)

    assert response.status_code == 404, "Expected status code 404, but got a different value"

    expected_detail = {"detail": "Comment not found"}
    assert response.json() == expected_detail, f"Expected {expected_detail}, got {response.json()}"

@pytest.mark.asyncio
async def test_add_like_for_comment(client, db_session, seed_database):
    auth = AuthTestHelper(client, db_session)
    headers = await auth.get_auth_headers(group_name=UserGroupEnum.USER)
    movie_id = 1
    data = {
        "text": "test comment for movie",
    }

    response = await client.post(f"/comment/{movie_id}/", headers=headers, json=data)
    assert response.status_code == 201, "Expected status code 201, but got a different value"

    comment_id = 1
    data = {
        "is_like": True,
    }

    response = await client.post(f"/{comment_id}/like/", headers=headers, json=data)
    assert response.status_code == 200, "Expected status code 200, but got a different value"

    stmt = select(CommentModel).where(CommentModel.id == comment_id)
    result = await db_session.execute(stmt)
    comment = result.scalar()
    assert comment is not None, (
        "Expected comment to be present when is_like is True, but got None"
    )

    assert comment.likes_count > 0, "Expected like_count > 0, but got 0"

    response = await client.post(f"/{comment_id}/like/", headers=headers, json=data)
    assert response.status_code == 200, "Expected status code 200, but got a different value"

    await db_session.refresh(comment)

    assert comment.likes_count == 0, f"Expected like_count == 0, but got {comment.likes_count}"


@pytest.mark.asyncio
async def test_add_dislike_for_comment(client, db_session, seed_database):
    auth = AuthTestHelper(client, db_session)
    headers = await auth.get_auth_headers(group_name=UserGroupEnum.USER)
    movie_id = 1
    data = {
        "text": "test comment for movie",
    }

    response = await client.post(f"/comment/{movie_id}/", headers=headers, json=data)
    assert response.status_code == 201, "Expected status code 201, but got a different value"

    comment_id = 1
    data = {
        "is_like": False,
    }

    response = await client.post(f"/{comment_id}/like/", headers=headers, json=data)
    assert response.status_code == 200, "Expected status code 200, but got a different value"

    stmt = select(CommentModel).where(CommentModel.id == comment_id)
    result = await db_session.execute(stmt)
    comment = result.scalar()
    assert comment is not None, (
        "Expected comment to be present when is_like is False, but got None"
    )

    assert comment.dislikes_count > 0, "Expected dislikes_count > 0, but got 0"

    response = await client.post(f"/{comment_id}/like/", headers=headers, json=data)
    assert response.status_code == 200, "Expected status code 200, but got a different value"

    await db_session.refresh(comment)

    assert comment.dislikes_count == 0, f"Expected dislikes_count == 0, but got {comment.likes_count}"


