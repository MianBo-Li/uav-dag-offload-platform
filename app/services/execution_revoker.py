import logging

logger = logging.getLogger(__name__)


class ExecutionRevoker:
    def revoke(self, celery_task_id: str) -> bool:
        from app.worker.celery_app import celery_app

        try:
            celery_app.control.revoke(celery_task_id, terminate=False)
        except Exception:
            logger.warning(
                "Failed to revoke Celery task %s",
                celery_task_id,
                exc_info=True,
            )
            return False
        return True
