from celery.worker.state import total_count
from fastapi import APIRouter, Query, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.exc import IntegrityError
from typing import Optional

from sqlalchemy.sql.functions import current_user
from starlette import status

from src.schemas.accounts import MessageResponseSchema
from src.database.models.accounts import UserModel
from src.dependencies.user import get_user_group, get_current_user
from src.dependencies.movies import get_movie_or_404, Pagination, search_movies, build_page_url, get_or_create, logic_like, search_favotite_movie
from src.database.engine import get_db
from src.database.models.movies import (
    MovieModel,
    CertificationModel,
    GenreModel,
    StarModel,
    DirectorModel,
    MovieRatingModel,
    MovieLikeModel)

from src.schemas.movies import (
    MovieListResponseSchema,
    MovieListItemSchema,
    MovieDetailResponseSchema,
    MovieLikeRequestSchema,
    MovieLikeResponseSchema,
    MovieCreateRequestSchema,
    MovieUpdateSchema,
    MovieRatingResponseSchema,
    MovieRatingRequestSchema,
    MovieLikeResponseSchema,
    GetFavoriteMoviesSchema,
)

router = APIRouter(tags=["Movies"])


@router.get("/movies/", response_model=MovieListResponseSchema)
async def get_movies_list(
    pagination: Pagination = Depends(),
    base_query = Depends(search_movies),
    search: Optional[str] = Query(None, description="Search by title, description, actor, or director"),
    db: AsyncSession = Depends(get_db),
):

    total_items = await pagination.get_total_items(db, base_query)
    if total_items == 0:
        raise HTTPException(status_code=404, detail="No movies found.")

    order_by = MovieModel.default_order_by()
    if order_by:
        base_query = base_query.order_by(*order_by)

    movies = await pagination.get_paginated_items(db, base_query)

    if not movies:
        raise HTTPException(status_code=404, detail="No movies found for this page.")

    movie_list = [MovieListItemSchema.model_validate(movie) for movie in movies]

    total_pages = (total_items + pagination.limit - 1) // pagination.limit

    response = MovieListResponseSchema(
        movies=movie_list,
        prev_page=build_page_url("movies", pagination.page - 1, pagination.limit, search) if pagination.page > 1 else None,
        next_page=build_page_url("movies", pagination.page + 1, pagination.limit, search) if pagination.page < total_pages else None,
        total_pages=total_pages,
        total_items=total_items,
    )
    return response


@router.post("/movies/", response_model=MovieDetailResponseSchema)
async def create_movie(
    movie_data: MovieCreateRequestSchema,
    db: AsyncSession = Depends(get_db),
    curret_user: UserModel = Depends(get_user_group),
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


@router.get("/movies/{movie_id}", response_model=MovieDetailResponseSchema)
async def get_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(MovieModel)
        .where(MovieModel.id == movie_id)
        .options(
            joinedload(MovieModel.certification),
            joinedload(MovieModel.genres),
            joinedload(MovieModel.stars),
            joinedload(MovieModel.directors),
        )
    )

    result = await db.execute(stmt)
    movie = result.scalars().first()
    if not movie:
        raise HTTPException(
            status_code=404, detail="Movie with the given ID was not found."
        )

    return MovieDetailResponseSchema.model_validate(movie)


@router.delete("/movies/{movie_id}")
async def delete_movie(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
    curret_user: UserModel = Depends(get_user_group),
):
    stmt = select(MovieModel).where(MovieModel.id == movie_id)
    result = await db.execute(stmt)
    movie = result.scalars().first()
    if not movie:
        raise HTTPException(
            status_code=404, detail="Movie with the given ID was not found."
        )

    await db.delete(movie)
    await db.commit()

    return {"detail": "Movie deleted successfully."}


@router.patch("/movies/{movie_id}")
async def update_movie(
    movie_data: MovieUpdateSchema,
    movie: MovieModel = Depends(get_movie_or_404),
    db: AsyncSession = Depends(get_db),
    curret_user: UserModel = Depends(get_user_group),
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


@router.post("/movies/{movie_id}/rating", response_model=MovieRatingResponseSchema)
async def add_movie_rating(
    data: MovieRatingRequestSchema,
    movie: MovieModel = Depends(get_movie_or_404),
    db: AsyncSession = Depends(get_db),
    curret_user: UserModel = Depends(get_current_user),
):

    stmt = select(MovieRatingModel).filter(
        MovieRatingModel.user_id == curret_user.id,
        MovieRatingModel.movie_id == movie.id,
    )
    result = await db.execute(stmt)
    rating = result.scalar_one_or_none()
    if rating:
        raise HTTPException(status_code=400, detail="Rating already exists.")
    else:
        rating = MovieRatingModel(
            movie_id=movie.id,
            user_id=curret_user.id,
            score=data.score,
        )
        db.add(rating)
    await db.flush()

    avg_score_stmt = select(func.avg(MovieRatingModel.score)).where(
        MovieRatingModel.movie_id == movie.id
    )
    avg_score_result = await db.execute(avg_score_stmt)
    avg_score = avg_score_result.scalar_one_or_none()
    movie.meta_score = round(float(avg_score), 2)
    await db.commit()
    return MovieRatingResponseSchema(movie_id=movie.id, meta_score=movie.meta_score)


@router.post("/movies/{movie_id}/favorite/", response_model=MessageResponseSchema)
async def add_in_favorite_movie(
    movie: MovieModel = Depends(get_movie_or_404),
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    stmt = (
        select(UserModel)
        .options(selectinload(UserModel.favorites))
        .where(UserModel.id == current_user.id)
    )
    result = await db.execute(stmt)
    if movie in current_user.favorites:
        raise HTTPException(status_code=400, detail="Movie already favorited")

    current_user.favorites.append(movie)
    await db.commit()
    return {"message": "Movie added to favorites"}


@router.get(
    "/movies/favorites/",
)
async def get_favorite_movies(
    current_user: UserModel = Depends(get_current_user),
    base_query = Depends(search_favotite_movie),
    search: Optional[str] = Query(
            None, description="Search by title, description, actor, or director"),
    pagination: Pagination = Depends(),
    db: AsyncSession = Depends(get_db),
):
    total_items = await pagination.get_total_items(db, base_query)
    total_pages = (total_items + pagination.limit - 1) // pagination.limit if total_items > 0 else 1

    paginated_stmt = (
        base_query
        .limit(pagination.limit)
        .offset(pagination.offset)
    )

    result = await db.execute(paginated_stmt)
    movies = result.scalars().all()

    movie_list = [MovieListItemSchema.model_validate(movie) for movie in movies]

    return GetFavoriteMoviesSchema(
        movies=movie_list,
        prev_page=build_page_url("/movies/favorites/", pagination.page - 1, pagination.limit,
                                 search) if pagination.page > 1 else None,
        next_page=build_page_url("/movies/favorites/", pagination.page + 1, pagination.limit,
                                 search) if pagination.page < total_pages else None,
        total_pages=total_pages,
        total_items=total_items,

    )


@router.delete("/movies/{movie_id}/favorites/", response_model=MessageResponseSchema)
async def remove_favorite_movie(
    movie: MovieModel = Depends(get_movie_or_404),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(UserModel)
        .options(selectinload(UserModel.favorites))
        .where(UserModel.id == current_user.id)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if movie not in user.favorites:
        raise HTTPException(status_code=400, detail="Movie not found.")
    current_user.favorites.remove(movie)
    await db.commit()
    return {"message": "Movie removed from favorites"}


@router.post("/movies/{movie_id}/like", response_model=MovieLikeResponseSchema)
async def add_movie_like(
    request_like: MovieLikeRequestSchema,
    movie: MovieModel = Depends(get_movie_or_404),
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    movie = await logic_like(
        db=db,
        model_in_db=movie,
        user=current_user,
        request_like=request_like.is_like,
        like_model=MovieLikeModel,
        name_relation="movie_id"
    )

    return MovieLikeResponseSchema(
        movie_id=movie.id,
        like=movie.likes_count,
        dislike=movie.dislikes_count,
    )
