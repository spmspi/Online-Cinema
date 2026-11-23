from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient

from src.database.models.accounts import UserModel, UserGroupModel, UserGroupEnum


class AuthTestHelper:
    def __init__(self, client: AsyncClient, db_session: AsyncSession, login_url: str = "/login/"):
        self.client = client
        self.db_session = db_session
        self.login_url = login_url

    async def create_user(
        self,
        email: str = "testuser@example.com",
        password: str = "StrongPassword123!",
        group_name: UserGroupEnum = UserGroupEnum.ADMIN,
        is_active: bool = True,
    ) -> UserModel:
        stmt = select(UserGroupModel).where(UserGroupModel.name == group_name)
        result = await self.db_session.execute(stmt)
        group = result.scalars().first()
        assert group is not None, f"User group {group_name} should exist."

        user = UserModel.create(
            email=email,
            raw_password=password,
            group_id=group.id,
        )
        user.is_active = is_active
        self.db_session.add(user)
        await self.db_session.commit()
        return user

    async def login(self, email: str, password: str) -> dict:
        response = await self.client.post(
            self.login_url,
            json={"email": email, "password": password},
        )
        assert response.status_code == 200, f"Login failed: {response.status_code}, {response.text}"
        return response.json()

    async def get_access_token(self, email: str, password: str) -> str:
        data = await self.login(email, password)
        assert "access_token" in data, f"Missing 'access_token' in response: {data}"
        return data["access_token"]

    async def get_auth_headers(
        self,
        email: str = "testuser@example.com",
        password: str = "StrongPassword123!",
        group_name: UserGroupEnum = UserGroupEnum.ADMIN,
    ) -> dict[str, str]:
        await self.create_user(email=email, password=password, group_name=group_name)
        token = await self.get_access_token(email=email, password=password)
        return {"Authorization": f"Bearer {token}"}