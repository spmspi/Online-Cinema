from fastapi import APIRouter, Query, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
from typing import Optional

from src.database.models.accounts import UserModel
from src.dependencies import get_user_group
from src.database.engine import get_db
from src.database.models.movies import MovieModel, CertificationModel, GenreModel, StarModel, DirectorModel
from src.schemas.movies import MovieListResponseSchema, MovieListItemSchema, MovieDetailResponseSchema, \
    MovieCreateRequestSchema, MovieUpdateSchema

router = APIRouter()


@router.get("/movies/", response_model=MovieListResponseSchema)
async def get_movies_list(
        page: int = Query(1, ge=1),
        limit: int = Query(10, ge=1, le=20),
        search: Optional[str] = Query(None, description="Search by title, description, actor, or director"),
        db: AsyncSession = Depends(get_db)
):
    offset = (page - 1) * limit

    base_query = select(MovieModel)

    if search:
        search_query = f"%{search}%"
        search_filter = or_(
            MovieModel.name.ilike(search_query),
            MovieModel.description.ilike(search_query),
            MovieModel.stars.any(StarModel.name.ilike(search_query)),
            MovieModel.directors.any(DirectorModel.name.ilike(search_query))
        )
        base_query = base_query.where(search_filter)

    count_stmt = select(func.count()).select_from(base_query.subquery())
    result_count = await db.execute(count_stmt)
    total_items = result_count.scalar() or 0

    if total_items == 0:
        raise HTTPException(status_code=404, detail="No movies found.")

    order_by = MovieModel.default_order_by()
    if order_by:
        base_query = base_query.order_by(*order_by)

    paginated_stmt = base_query.offset(offset).limit(limit)

    result_movies = await db.execute(paginated_stmt)
    movies = result_movies.scalars().all()

    if not movies:
        raise HTTPException(status_code=404, detail="No movies found for this page.")

    movie_list = [MovieListItemSchema.model_validate(movie) for movie in movies]

    total_pages = (total_items + limit - 1) // limit

    def build_page_url(target_page: int) -> str:
        url = f"/theater/movies/?page={target_page}&limit={limit}"
        if search:
            url += f"&search={search}"
        return url

    response = MovieListResponseSchema(
        movies=movie_list,
        prev_page=build_page_url(page - 1) if page > 1 else None,
        next_page=build_page_url(page + 1) if page < total_pages else None,
        total_pages=total_pages,
        total_items=total_items,
    )
    return response


@router.post("/movies/", response_model=MovieDetailResponseSchema)
async def create_movie(
        movie_data: MovieCreateRequestSchema,
        db: AsyncSession = Depends(get_db),
        curret_user: UserModel = Depends(get_user_group)
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
                    )
                )

    try:
        certification_stmt = select(CertificationModel).where(CertificationModel.name == movie_data.certification)
        certification_res = await db.execute(certification_stmt)
        certification = certification_res.scalars().first()
        if not certification:
            certification = CertificationModel(name=movie_data.certification)
            db.add(certification)
            await db.flush()

        genres = []
        for genres_name in movie_data.genres:
            genre_stmt = select(GenreModel).where(GenreModel.name == genres_name)
            genre_res = await db.execute(genre_stmt)
            genre = genre_res.scalars().first()
            if not genre:
                genre = GenreModel(name=genres_name)
                db.add(genre)
                await db.flush()
            genres.append(genre)

        stars = []
        for star_name in movie_data.stars:
            star_stmt = select(StarModel).where(StarModel.name == star_name)
            star_res = await db.execute(star_stmt)
            star = star_res.scalars().first()
            if not star:
                star = StarModel(name=star_name)
                db.add(star)
                await db.flush()
            stars.append(star)

        directors = []
        for director_name in movie_data.directors:
            director_stmt = select(DirectorModel).where(DirectorModel.name == director_name)
            director_res = await db.execute(director_stmt)
            director = director_res.scalars().first()
            if not director:
                director = DirectorModel(name=director_name)
                db.add(director)
                db.flush()
            directors.append(director)

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
    stmt = select(MovieModel).where(MovieModel.id == movie_id).options(
        joinedload(MovieModel.certification),
        joinedload(MovieModel.genres),
        joinedload(MovieModel.stars),
        joinedload(MovieModel.directors)
    )

    result = await db.execute(stmt)
    movie = result.scalars().first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie with the given ID was not found.")

    return MovieDetailResponseSchema.model_validate(movie)

@router.delete("/movies/{movie_id}")
async def delete_movie(movie_id: int, db: AsyncSession = Depends(get_db),
                       curret_user: UserModel = Depends(get_user_group)):
    stmt = select(MovieModel).where(MovieModel.id == movie_id)
    result = await db.execute(stmt)
    movie = result.scalars().first()
    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie with the given ID was not found."
        )

    await db.delete(movie)
    await db.commit()

    return {"detail": "Movie deleted successfully."}


@router.patch("/movies/{movie_id}")
async def update_movie(
        movie_id: int,
        movie_data: MovieUpdateSchema,
        db: AsyncSession = Depends(get_db),
        curret_user: UserModel = Depends(get_user_group)
):
    stmt = select(MovieModel).where(MovieModel.id == movie_id)
    result = await db.execute(stmt)
    movie = result.scalars().first()

    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie with the given ID was not found."
        )

    for field, value in movie_data.model_dump(exclude_unset=True).items():
        setattr(movie, field, value)

    try:
        await db.commit()
        await db.refresh(movie)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Invalid input data.")

    return {"detail": "Movie updated successfully."}