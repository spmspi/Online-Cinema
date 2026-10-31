import asyncio


from datetime import datetime
from sqlalchemy import delete

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
