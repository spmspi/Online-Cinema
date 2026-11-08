from typing import List, Optional

from fastapi import Depends, HTTPException, Query

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.testing.pickleable import User

from src.dependencies.user import get_current_user
from src.database.models.accounts import UserModel
from src.database.models.movies import MovieModel, StarModel, DirectorModel
from src.database.engine import get_db


async def get_movie_or_404(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(MovieModel).where(MovieModel.id == movie_id)
    result = await db.execute(stmt)
    movie = result.scalar_one_or_none()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found.")
    return movie


class Pagination:
    def __init__(self,
                 page: int = Query(1, ge=1),
                 limit: int = Query(10, ge=1, le=20),
                 ):
        self.page = page
        self.limit = limit

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


    async def get_total_items(self, db: AsyncSession, base_query) -> int:
        count_stmt = select(func.count()).select_from(base_query.subquery())
        result_count = await db.execute(count_stmt)
        total_items = result_count.scalar() or 0
        return total_items

    async def get_paginated_items(self, db: AsyncSession, base_query):
        paginated_stmt = base_query.offset(self.offset).limit(self.limit)
        result = await db.execute(paginated_stmt)
        items = result.scalars().all()
        return items


async def search_movies(
        search: Optional[str] = Query(
        None, description="Search by title, description, actor, or director"
    ),
    db: AsyncSession = Depends(get_db),
):
    base_query = select(MovieModel)
    if search:
        search_query = f"%{search}%"
        search_filter = or_(
            MovieModel.name.ilike(search_query),
            MovieModel.description.ilike(search_query),
            MovieModel.stars.any(StarModel.name.ilike(search_query)),
            MovieModel.directors.any(DirectorModel.name.ilike(search_query)),
        )
        base_query = base_query.where(search_filter)
    return base_query


async def search_favotite_movie(
        search: Optional[str] = Query(
            None, description="Search by title, description, actor, or director"),
        db: AsyncSession = Depends(get_db),
        user: UserModel = Depends(get_current_user) ):
    base_query = (
        select(MovieModel)
        .join(UserModel.favorites)
        .where(UserModel.id == user.id)
    )

    if search:
        search_query = f"%{search}%"
        search_filter = or_(
            MovieModel.name.ilike(search_query),
            MovieModel.description.ilike(search_query),
            MovieModel.stars.any(StarModel.name.ilike(search_query)),
            MovieModel.directors.any(DirectorModel.name.ilike(search_query)),
        )
        base_query = base_query.where(search_filter)
    return base_query


def build_page_url(base_page: str, target_page: int, limit: int, search: Optional[str] = None) -> str:
    url = f"/{base_page}/?page={target_page}&limit={limit}"
    if search:
        url += f"&search={search}"
    return url


async def get_or_create(db: AsyncSession, model, name: str):
    stmt = select(model).where(model.name == name)
    result = await db.execute(stmt)
    instance = result.scalars().first()

    if not instance:
        instance = model(name=name)
        db.add(instance)
        await db.flush()

    return instance

async def logic_like(
        db: AsyncSession,
        model_in_db,
        user,
        request_like,
        like_model,
        name_relation,
):
    stmt = select(like_model).filter(
        getattr(like_model, "user_id") == user.id,
        getattr(like_model, name_relation) == model_in_db.id
    )
    result = await db.execute(stmt)
    like_in_db = result.scalar_one_or_none()
    if like_in_db:
        if like_in_db.is_like == request_like:
            if like_in_db.is_like:
                model_in_db.likes_count -= 1
            else:
                model_in_db.dislikes_count -= 1
            await db.delete(like_in_db)
        else:
            like_in_db.is_like = request_like
            if request_like:
                model_in_db.likes_count += 1
                model_in_db.dislikes_count -= 1
            else:
                model_in_db.dislikes_count += 1
                model_in_db.likes_count -= 1
            await db.commit()
    else:
        new_like = like_model(**{
            name_relation:model_in_db.id,
            "user_id":user.id,
            "is_like":request_like,
        })
        db.add(new_like)
        if request_like:
            model_in_db.likes_count += 1
        else:
            model_in_db.dislikes_count += 1
    await db.commit()
    await db.refresh(model_in_db)
    return model_in_db