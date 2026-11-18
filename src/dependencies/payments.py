from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette import status
from sqlalchemy import select

from src.database.models.order import StatusOrderEnum
from src.database.models.order import OrdersModel, OrderItemModel
from src.database.models.accounts import UserModel
from src.dependencies.user import get_current_user
from src.database.engine import get_db


async def pay_order(
    user: UserModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(OrdersModel)
        .where(OrdersModel.user_id == user.id)
        .where(OrdersModel.status == StatusOrderEnum.PENDING)
        .options(
            selectinload(OrdersModel.order_items).selectinload(OrderItemModel.movie),
        )
    )
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )
    return order
