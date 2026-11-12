import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import delete, select

from src.database.models.accounts import UserModel
from src.database.models.cart import CartModel
from src.database.models.movies import MovieModel
from src.database.models.order import OrdersModel, StatusOrderEnum
from src.session_postgres import SyncSessionLocal
from src.database.models.accounts import RefreshTokenModel
from src.celery.celery_app import celery_app


@celery_app.task(name="src.celery.tasks.cleanup_tokens_task")
def cleanup_tokens_task():
    with SyncSessionLocal() as session:
        with session.begin():
            stmt = delete(RefreshTokenModel).where(RefreshTokenModel.expires_at < datetime.now())
            result = session.execute(stmt)
            session.commit()

@celery_app.task(name="src.celery.tasks.check_status_order_task")
def check_status_order_task():
    with SyncSessionLocal() as session:
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        stmt = select(OrdersModel).where(OrdersModel.status == StatusOrderEnum.PENDING).where(OrdersModel.created_at <= one_hour_ago)
        expired = session.execute(stmt).scalars().all()
        for order in expired:
            order.status = StatusOrderEnum.CANCELED
        if expired:
            session.commit()

