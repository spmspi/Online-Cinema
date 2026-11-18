from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from src.dependencies.comments import get_comment_or_404, get_sub_comment_or_404
from src.database.models.accounts import UserModel
from src.dependencies.user import get_current_user
from src.dependencies.movies import get_movie_or_404, logic_like, Pagination, build_page_url
from src.database.engine import get_db
from src.database.models.movies import MovieModel
from src.schemas.comments import (
    CommentRequestSchema,
    CommentResponseSchema,
    GetMovieCommentsResponseSchema,
    ResponseSubCommentSchema,
    GetSubCommentsResponseSchema,
    SubCommetBaseSchema, CommentLikeRequestSchema, CommentLikeResponseSchema,
)
from src.database.models.comments import CommentModel, SubCommentModel, CommentLikeModel, SubCommentLikeModel

router = APIRouter(tags=["Comments"])


@router.post("/comment/{movie_id}/", response_model=CommentResponseSchema)
async def add_movie_comment(
    comment: CommentRequestSchema,
    movie: MovieModel = Depends(get_movie_or_404),
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    try:
        new_comment = CommentModel(
            text=comment.text, user_id=current_user.id, movie_id=movie.id
        )
        db.add(new_comment)
        await db.commit()
        await db.refresh(new_comment)

        return CommentResponseSchema(
            id=new_comment.id,
            movie_id=movie.id,
            user_id=current_user.id,
            text=new_comment.text,
            created_at=new_comment.created_at,
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"something went wrong {e}")


@router.get(
    "/comments/{movie_id}/", response_model=GetMovieCommentsResponseSchema
)
async def get_movie_comments(
    movie: MovieModel = Depends(get_movie_or_404),
    pagination: Pagination = Depends(),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(CommentModel)
        .filter(CommentModel.movie_id == movie.id)
        .options(
            selectinload(CommentModel.user),
            selectinload(CommentModel.sub_comments).selectinload(SubCommentModel.user),
            selectinload(CommentModel.likes),
        )
    )
    comments = await pagination.get_paginated_items(db, stmt)
    comments_list = [CommentResponseSchema.model_validate(com) for com in comments]
    total_items = await pagination.get_total_items(db, stmt)
    total_pages = (total_items + pagination.limit - 1) // pagination.limit
    response = GetMovieCommentsResponseSchema(
        comments=comments_list,
        prev_page=build_page_url("comments", pagination.page - 1, pagination.limit) if pagination.page > 1 else None,
        next_page=build_page_url("comments", pagination.page + 1, pagination.limit) if pagination.page < total_pages else None,
        total_pages=total_pages,
        total_items=total_items,
    )

    return response


@router.post(
    "/movie_comments/{comment_id}/", response_model=ResponseSubCommentSchema
)
async def add_sub_comment(
    comment: CommentRequestSchema,
    parent_comment: CommentModel = Depends(get_comment_or_404),
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    try:
        new_sub_comment = SubCommentModel(
            user_id=current_user.id,
            text=comment.text,
            comment_id=parent_comment.id,
        )

        db.add(new_sub_comment)
        await db.commit()
        await db.refresh(new_sub_comment)
        return ResponseSubCommentSchema(
            parent_comment=parent_comment, comments=new_sub_comment.text
        )
    except Exception:
        raise HTTPException(status_code=404, detail="something went wrong")


@router.get("/movie_comments/{comment_id}/", response_model=GetSubCommentsResponseSchema)
async def get_sub_comment(
    comment_in_db: CommentModel = Depends(get_comment_or_404),
    pagination: Pagination = Depends(),
    db: AsyncSession = Depends(get_db),
):
    try:
        stmt_sub = (
            select(SubCommentModel)
            .filter(SubCommentModel.comment_id == comment_in_db.id)
            .options(joinedload(SubCommentModel.user))
        )

        result = await db.execute(stmt_sub)
        comments = result.scalars().all()
        comments_list = [SubCommetBaseSchema.model_validate(com) for com in comments]
        total_items = await pagination.get_total_items(db, stmt_sub)
        total_pages = (total_items + pagination.limit - 1) // pagination.limit
        return GetSubCommentsResponseSchema(
            parent_comment=comment_in_db,
            comments=comments_list,
            prev_page=build_page_url(f"/movie_comments/{comment_in_db.id}/", pagination.page - 1,
                                     pagination.limit) if pagination.page > 1 else None,
            next_page=build_page_url(f"/movie_comments/{comment_in_db.id}/", pagination.page + 1,
                                     pagination.limit) if pagination.page < total_pages else None,
            total_pages=total_pages,
            total_items=total_items,

        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"something went wrong {e}")



@router.post("/{comment_id}/like", response_model=CommentLikeResponseSchema)
async def add_comment_like(
    request_like: CommentLikeRequestSchema,
    comment_in_db: CommentModel = Depends(get_comment_or_404),
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    update_like = await logic_like(
        db=db,
        model_in_db=comment_in_db,
        user=current_user,
        request_like=request_like.is_like,
        like_model=CommentLikeModel,
        name_relation="comment_id"
    )

    return CommentLikeResponseSchema(
        comment_id=update_like.id,
        like=update_like.likes_count,
        dislike=update_like.dislikes_count,
    )


@router.post("/{sub_comment_id}/like", response_model=CommentLikeResponseSchema)
async def add_sub_comment_like(
    request_like: CommentLikeRequestSchema,
    sub_comment_in_db: SubCommentModel = Depends(get_sub_comment_or_404),
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    new_sub_like = await logic_like(
        db=db,
        model_in_db=sub_comment_in_db,
        user=current_user,
        request_like=request_like.is_like,
        like_model=SubCommentLikeModel,
        name_relation="sub_comment_id"
    )

    return CommentLikeResponseSchema(
        comment_id=new_sub_like.id,
        like=new_sub_like.likes_count,
        dislike=new_sub_like.dislikes_count,
    )



