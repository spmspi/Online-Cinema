
from fastapi import APIRouter, Query, HTTPException, Depends

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from starlette import status

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


