from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.functions import current_user
from starlette import status
from sqlalchemy import select, func, or_, delete

from src.schemas.movies import MovieListSchema
from src.schemas.accounts import MessageResponseSchema
from src.database.models.accounts import UserModel
from src.dependencies.user import get_current_user, get_admin_user_group
from src.database.models.cart import CartItemModel
from src.database.models.movies import MovieModel
from src.dependencies.movies import get_movie_or_404
from src.dependencies.cart import get_cart_in_current_user, get_cart_admin
from src.schemas.cart import CartBaseSchema, CartListResponseSchema
from src.database.engine import get_db
from src.database.models.cart import CartModel


async def clear_cart_db(
        cart: CartModel = Depends(get_cart_in_current_user),
        db: AsyncSession = Depends(get_db),
):
    stmt = select(CartItemModel).where(CartItemModel.cart_id == cart.id)
    result = await db.execute(stmt)
    cart_item = result.scalars().all()
    if not cart_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="The cart is empty")

    else:
        stmt_del = delete(CartItemModel).where(CartItemModel.cart_id == cart.id)
        await db.execute(stmt_del)
    await db.commit()
