from typing import Optional

from fastapi import APIRouter, Query, HTTPException, Depends

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.exc import IntegrityError
from starlette import status

from src.schemas.admin import AdminOrderDetailSchema
from src.schemas.order import OrderDetailSchema, OrderSchema
from src.database.models.order import OrdersModel
from src.database.models.accounts import UserModel, UserGroupModel
from src.schemas.accounts import MessageResponseSchema, ActivateAccountRequestSchema, ChangeGroupSchema
from src.database.models.order import OrderItemModel, StatusOrderEnum
from src.dependencies.user import get_admin_user_group
from src.dependencies.movies import get_movie_or_404, get_or_create
from src.database.engine import get_db
from src.database.models.movies import (
    MovieModel,
    CertificationModel,
    GenreModel,
    StarModel,
    DirectorModel)

from src.schemas.movies import (
    MovieDetailResponseSchema,
    MovieCreateRequestSchema,
    MovieUpdateSchema,
)

router = APIRouter(
    prefix="/admin",
    tags=["Admin Panel"],
    dependencies=[Depends(get_admin_user_group)]
)



@router.post("/movies/", response_model=MovieDetailResponseSchema)
async def create_movie(
    movie_data: MovieCreateRequestSchema,
    db: AsyncSession = Depends(get_db),
):
    movie_stmt = select(MovieModel).where(
        (MovieModel.name == movie_data.name),
        (MovieModel.year == movie_data.year),
        (MovieModel.time == movie_data.time),
    )
    result = await db.execute(movie_stmt)
    dublicate = result.scalar()
    if dublicate:
        raise HTTPException(
            status_code=409,
            detail=(
                f"A movie with the name '{movie_data.name}', release date "
                f"'{movie_data.year}', and {movie_data.time} minute already exists."
            ),
        )

    try:
        certification = await get_or_create(db, CertificationModel, movie_data.certification)

        genres = [await get_or_create(db, GenreModel, name) for name in movie_data.genres]
        stars = [await get_or_create(db, StarModel, name) for name in movie_data.stars]
        directors = [await get_or_create(db, DirectorModel, name) for name in movie_data.directors]

        movie = MovieModel(
            name=movie_data.name,
            year=movie_data.year,
            time=movie_data.time,
            imdb=movie_data.imdb,
            votes=movie_data.votes,
            meta_score=movie_data.meta_score,
            gross=movie_data.gross,
            description=movie_data.description,
            price=movie_data.price,
            certification=certification,
            genres=genres,
            stars=stars,
            directors=directors,
        )
        db.add(movie)
        await db.commit()
        await db.refresh(movie, ["genres", "stars", "directors"])
        return MovieDetailResponseSchema.model_validate(movie)

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"{e}")



@router.delete("/movies/{movie_id}")
async def delete_movie(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(MovieModel)
        .where(MovieModel.id == movie_id)
        .options(
            selectinload(MovieModel.order_items).selectinload(OrderItemModel.order)
        )
    )
    result = await db.execute(stmt)
    movie = result.scalar_one_or_none()

    if not movie:
        raise HTTPException(
            status_code=404, detail="Movie with the given ID was not found."
        )

    for item in movie.order_items:
        order = item.order
        if order and order.status in (StatusOrderEnum.PENDING, StatusOrderEnum.PAID):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"The film cannot be deleted because it is part of an order with a status of '{order.status.name}'."
            )

    await db.delete(movie)
    await db.commit()

    return {"detail": "Movie deleted successfully."}


@router.patch("/movies/{movie_id}")
async def update_movie(
    movie_data: MovieUpdateSchema,
    movie: MovieModel = Depends(get_movie_or_404),
    db: AsyncSession = Depends(get_db),
):

    for field, value in movie_data.model_dump(exclude_unset=True).items():
        setattr(movie, field, value)

    try:
        await db.commit()
        await db.refresh(movie)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Invalid input data.")

    return {"detail": "Movie updated successfully."}



@router.post(
    "/activate_account/",
    response_model=MessageResponseSchema,
)
async def activate_account(
        email: ActivateAccountRequestSchema,
        db: AsyncSession = Depends(get_db),
):
    stmt = select(UserModel).filter_by(email=email.email)
    result = await db.execute(stmt)
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    if user.is_active == True:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account is already activated.",
        )
    user.is_active = True
    await db.commit()
    return MessageResponseSchema(message="Activated successfully.")



@router.post(
    "/group_change/",
    response_model=MessageResponseSchema,
)
async def group_change(
    data: ChangeGroupSchema,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(UserModel)
        .where(UserModel.email == data.email)
        .options(joinedload(UserModel.group))
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    if user.is_active == False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account has not been activated.",
        )

    stmt_group = select(UserGroupModel).filter_by(name=data.role)
    group_result = await db.execute(stmt_group)
    group_obj = group_result.scalar_one_or_none()

    if not group_obj:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Specified group not found.",
        )
    user.group = group_obj

    await db.commit()
    return MessageResponseSchema(message="Changed successfully.")


@router.get("/orders/", response_model=AdminOrderDetailSchema)
async def get_orders_user(
    status: Optional[StatusOrderEnum] = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(OrdersModel)
    if status:
        stmt = stmt.where(OrdersModel.status == status)
    stmt = stmt.order_by(OrdersModel.created_at)

    result = await db.execute(stmt)
    orders = result.scalars().all()

    order_list = [OrderSchema.model_validate(order) for order in orders]

    return AdminOrderDetailSchema(
        total=len(order_list),
        orders=order_list,
    )



