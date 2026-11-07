from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.database.engine import get_db
from src.database.models.comments import CommentModel, SubCommentModel, CommentLikeModel, SubCommentLikeModel
from sqlalchemy.ext.asyncio import AsyncSession

async def get_comment_or_404(comment_id: int, db: AsyncSession = Depends(get_db)) -> CommentModel:
    stmt = select(CommentModel).filter(CommentModel.id == comment_id).options(selectinload(CommentModel.likes))
    result = await db.execute(stmt)
    parent_comment = result.scalar_one_or_none()
    if not parent_comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    return parent_comment


async def get_sub_comment_or_404(sub_comment_id: int, db: AsyncSession = Depends(get_db)) -> SubCommentModel:
    stmt = select(SubCommentModel).filter(SubCommentModel.id == sub_comment_id).options(selectinload(SubCommentModel.likes))
    result = await db.execute(stmt)
    sub_comment = result.scalar_one_or_none()
    if not sub_comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    return sub_comment
