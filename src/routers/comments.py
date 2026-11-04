from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from src.database.models.accounts import UserModel
from src.dependencies.user import get_current_user
from src.dependencies.movies import get_movie_or_404
from src.database.engine import get_db
from src.database.models.movies import MovieModel
from src.schemas.comments import (
    CommentRequestSchema,
    CommentResponseSchema,
    GetMovieCommentsResponseSchema,
    ResponseSubCommentSchema,
    GetSubCommentsResponseSchema,
    SubCommetBaseSchema,
)
from src.database.models.comments import CommentModel, SubCommentModel

router = APIRouter()


@router.post("/movies/{movie_id}/comment/", response_model=CommentResponseSchema)
async def add_movie_comment(
    comment: CommentRequestSchema,
    movie: MovieModel = Depends(get_movie_or_404),
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
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


@router.get(
    "/movies/{movie_id}/comments/", response_model=GetMovieCommentsResponseSchema
)
async def get_movie_comments(
    movie: MovieModel = Depends(get_movie_or_404),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(CommentModel)
        .filter(CommentModel.movie_id == movie.id)
        .options(
            selectinload(CommentModel.user),
            selectinload(CommentModel.sub_comments).selectinload(SubCommentModel.user),
        )
    )
    result = await db.execute(stmt)
    comments = result.scalars().all()
    comments_list = [CommentResponseSchema.model_validate(com) for com in comments]
    return GetMovieCommentsResponseSchema(
        comments=comments_list,
    )


@router.post(
    "/movies/{movie_id}/{comment_id}/", response_model=ResponseSubCommentSchema
)
async def add_sub_comment(
    comment: CommentRequestSchema,
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    stmt = select(CommentModel).filter(CommentModel.id == comment_id)
    result = await db.execute(stmt)
    parent_comment = result.scalar_one_or_none()
    if not parent_comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    new_sub_comment = SubCommentModel(
        user_id=current_user.id,
        text=comment.text,
        comment_id=comment_id,
    )

    db.add(new_sub_comment)
    await db.commit()
    await db.refresh(new_sub_comment)
    return ResponseSubCommentSchema(
        parent_comment=parent_comment, comments=new_sub_comment.text
    )


@router.get("/movies/{comment_id}/", response_model=GetSubCommentsResponseSchema)
async def get_sub_comment(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CommentModel).filter(CommentModel.id == comment_id)
    result = await db.execute(stmt)
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    stmt_sub = (
        select(SubCommentModel)
        .filter(SubCommentModel.comment_id == comment_id)
        .options(joinedload(SubCommentModel.user))
    )

    result = await db.execute(stmt_sub)
    comments = result.scalars().all()
    comments_list = [SubCommetBaseSchema.model_validate(com) for com in comments]

    return GetSubCommentsResponseSchema(parent_comment=comment, comments=comments_list)
