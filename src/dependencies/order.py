from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette import status
from sqlalchemy import select, func, or_, delete

from src.database.models.order import OrdersModel, OrderItemModel, StatusOrderEnum
from src.database.models.accounts import UserModel
from src.dependencies.user import get_current_user
from src.database.models.cart import CartItemModel
from src.dependencies.cart import get_cart_in_current_user
from src.database import get_db
from src.database.models.cart import CartModel


async def clear_cart_db(
    cart: CartModel = Depends(get_cart_in_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CartItemModel).where(CartItemModel.cart_id == cart.id)
    result = await db.execute(stmt)
    cart_item = result.scalars().all()
    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="The cart is empty"
        )

    else:
        stmt_del = delete(CartItemModel).where(CartItemModel.cart_id == cart.id)
        await db.execute(stmt_del)
    await db.commit()


async def get_order_by_id(
    order_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(OrdersModel)
        .where(OrdersModel.id == order_id)
        .filter(OrdersModel.user_id == current_user.id)
        .options(
            selectinload(OrdersModel.order_items).selectinload(OrderItemModel.movie)
        )
    )
    res = await db.execute(stmt)
    order = res.scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found."
        )

    return order


async def check_unpaid_order(
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
    total = 0
    if order:
        for item in order.order_items:
            current_price = item.movie.price
            if item.price_at_order != current_price:
                item.price_at_order = current_price
            total += item.price_at_order
        if order.total_amount != total:
            order.total_amount = total
            await db.commit()
            await db.refresh(order)
    return order
