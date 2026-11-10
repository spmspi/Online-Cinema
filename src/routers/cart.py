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

router = APIRouter(tags=["Cart"])


@router.get("/cart/", response_model=CartListResponseSchema)
async def get_cart(
    cart: CartModel = Depends(get_cart_in_current_user),
    db: AsyncSession = Depends(get_db),
):
    movie_list = [MovieListSchema.model_validate(item.movie) for item in cart.cart_items]
    return CartListResponseSchema(
        cart_id=cart.id,
        movies=movie_list,
    )



@router.post("/cart/{movie_id}", response_model=MessageResponseSchema)
async def add_movie_in_cart(
    cart: CartModel = Depends(get_cart_in_current_user),
    movie: MovieModel = Depends(get_movie_or_404),
    db: AsyncSession = Depends(get_db),
):
    try:
        cart_item = CartItemModel(cart_id=cart.id, movie_id=movie.id)
        db.add(cart_item)
        await db.commit()
        await db.refresh(cart_item)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This movie is already in the cart.",
        )
    return {"message": "movie added to cart"}


@router.delete("/cart/{movie_id}", response_model=MessageResponseSchema)
async def remove_movie_in_cart(
        cart: CartModel = Depends(get_cart_in_current_user),
        movie: MovieModel = Depends(get_movie_or_404),
        db: AsyncSession = Depends(get_db),
):
    stmt = select(CartItemModel).where(
        CartItemModel.cart_id == cart.id,
        CartItemModel.movie_id == movie.id
    )
    result = await db.execute(stmt)
    cart_item = result.scalar_one_or_none()
    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No cart with that id exists.",
        )
    await db.delete(cart_item)
    await db.commit()
    return {"message": "movie removed from cart"}


@router.delete("/cart/", response_model=MessageResponseSchema)
async def clear_cart(
        cart: CartModel = Depends(get_cart_in_current_user),
        db: AsyncSession = Depends(get_db),
):
    stmt = select(CartItemModel).where(CartItemModel.cart_id == cart.id)
    result = await db.execute(stmt)
    cart_item = result.scalars().all()
    if not cart_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="The trash has already been emptied.")

    else:
        stmt_del = delete(CartItemModel).where(CartItemModel.cart_id == cart.id)
        await db.execute(stmt_del)
    await db.commit()
    return {"message": "item removed from cart"}


@router.get("/cart/{user_id}", response_model=CartListResponseSchema)
async def get_cart_for_admin(
        user_id: int,
        cart: CartModel = Depends(get_cart_admin),
        current_user: UserModel = Depends(get_admin_user_group),
        db: AsyncSession = Depends(get_db),
):
    movie_list = [MovieListSchema.model_validate(item.movie) for item in cart.cart_items]
    return CartListResponseSchema(
        cart_id=cart.id,
        movies=movie_list,
    )