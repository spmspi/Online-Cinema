from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sqlalchemy.testing.pickleable import User

from src.database.models.cart import CartModel, CartItemModel
from src.dependencies.user import get_current_user

from src.database import get_db

async def get_cart_in_current_user(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(CartModel)
        .options(selectinload(CartModel.cart_items).selectinload(CartItemModel.movie))
        .where(CartModel.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    cart = result.scalar_one_or_none()
    if not cart:
        new_cart = CartModel(user_id=current_user.id)
        db.add(new_cart)
        await db.commit()

        stmt = (
            select(CartModel)
            .options(selectinload(CartModel.cart_items).selectinload(CartItemModel.movie))
            .where(CartModel.id == new_cart.id)
        )
        result = await db.execute(stmt)
        cart = result.scalar_one()

    return cart

async def get_cart_admin(user_id: int, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(CartModel)
        .options(selectinload(CartModel.cart_items).selectinload(CartItemModel.movie))
        .where(CartModel.user_id == user_id)
    )
    result = await db.execute(stmt)
    cart = result.scalar_one_or_none()
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cart or user not found"
        )
    return cart
