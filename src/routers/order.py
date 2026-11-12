from fastapi import APIRouter, Query, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.exc import IntegrityError
from typing import Optional

from sqlalchemy.sql.functions import current_user
from starlette import status

from src.database.models.movies import MovieModel
from src.schemas.movies import MovieListSchema
from src.dependencies.order import clear_cart_db, get_order_by_id
from src.schemas.order import OrderSchema, OrderListSchema, OrderDetailSchema
from src.dependencies.cart import get_cart_in_current_user
from src.database.models.cart import CartModel
from src.database.models.order import OrdersModel, StatusOrderEnum, OrderItemModel
from src.schemas.accounts import MessageResponseSchema
from src.database.models.accounts import UserModel
from src.dependencies.user import get_user_group, get_current_user
from src.dependencies.movies import get_movie_or_404, Pagination, search_movies, build_page_url, get_or_create, logic_like, search_favotite_movie
from src.database.engine import get_db

router = APIRouter(tags=["order"])


@router.post("/order/", response_model=OrderSchema)
async def create_order(
        cart: CartModel = Depends(get_cart_in_current_user),
        db: AsyncSession = Depends(get_db),
):
    try:
        order_items = []
        total_amount = 0
        for item in cart.cart_items:
            order_item = OrderItemModel(
                movie_id=item.movie_id,
                price_at_order=item.movie.price
            )
            total_amount += item.movie.price
            order_items.append(order_item)

        new_order = OrdersModel(
            user_id=cart.user_id,
            total_amount=total_amount,
            status=StatusOrderEnum.PENDING,
            order_items=order_items)


        db.add(new_order)
        await clear_cart_db(cart, db)
        await db.commit()
        await db.refresh(new_order)

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return OrderSchema.model_validate(new_order)


@router.get("/order/", response_model=OrderListSchema)
async def get_my_orders(
        user: UserModel = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    try:
        stmt = select(OrdersModel).where(OrdersModel.user_id == user.id)
        res = await db.execute(stmt)
        orders = res.scalars().all()
        orders_list = [OrderSchema.model_validate(order) for order in orders]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return OrderListSchema(
        user_id=user.id,
        orders=orders_list,
    )


@router.delete("/order/{order_id}", response_model=MessageResponseSchema)
async def delete_order(
        order_id: int,
        user: UserModel = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    stmt = select(OrdersModel).where(OrdersModel.id == order_id).filter(OrdersModel.user_id == user.id)
    res = await db.execute(stmt)
    order = res.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    await db.delete(order)
    await db.commit()
    return {"message": "order deleted"}

@router.get("/order/{order_id}/", response_model=OrderDetailSchema)
async def get_order_detail(
        order: OrdersModel = Depends(get_order_by_id),
        user: UserModel = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    stmt = select(OrdersModel).where(OrdersModel.id == order.id).options(
        selectinload(OrdersModel.order_items).selectinload(OrderItemModel.movie)
    )
    res = await db.execute(stmt)
    order = res.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    movie_list = [MovieListSchema.model_validate(item.movie) for item in order.order_items]
    return OrderDetailSchema(
        id=order.id,
        user_id=user.id,
        created_at=order.created_at,
        movies=movie_list,
    )

@router.patch("/order/{order_id}/cancel", response_model=MessageResponseSchema)
async def cancel_order(
    order: OrdersModel = Depends(get_order_by_id),
    db: AsyncSession = Depends(get_db),
):
    if order.status is StatusOrderEnum.PENDING:
        order.status = StatusOrderEnum.CANCELED
        await db.commit()
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="You cannot cancel an order if it has been paid for or has already been canceled.")
    return {"message": "order canceled"}
