from pwdlib import PasswordHash
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends


from src.database.engine import get_db
from src.database.models.accounts import UserModel

password_hash = PasswordHash.recommended()

DUMMY_HASH = password_hash.hash("dummypassword")

def verify_password(plain_password, hashed_password):
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password):
    return password_hash.hash(password)


async def authenticate_user(email: str, password: str, db: AsyncSession = Depends(get_db)):
    stmt = db.select(UserModel).where(UserModel.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        verify_password(password, DUMMY_HASH)
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user