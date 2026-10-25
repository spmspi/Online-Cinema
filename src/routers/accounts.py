from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.engine import get_db
from src.schemas.accounts import UserRegistrationRequestSchema

router = APIRouter()

@router.post("/register")
async def register_user(
        user_data: UserRegistrationRequestSchema,
        db: AsyncSession = Depends(get_db())):
    pass

