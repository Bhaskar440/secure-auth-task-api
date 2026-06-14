import time
import logging
from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def send_email_alert(self, recipient: str, subject: str, body: str):
    """
    Simulate sending an email alert.
    Replace with real SMTP / SendGrid logic in production.
    """
    try:
        logger.info(f"[EMAIL] Sending to {recipient}: {subject}")
        time.sleep(0.5)  # simulate network I/O
        logger.info(f"[EMAIL] Sent successfully to {recipient}")
        return {"status": "sent", "recipient": recipient}
    except Exception as exc:
        logger.error(f"[EMAIL] Failed: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def generate_report(self, task_id: int, owner_id: int):
    """
    Simulate async report generation for a task.
    Replace with actual report logic (PDF generation, S3 upload, etc.).
    """
    try:
        logger.info(f"[REPORT] Generating report for task_id={task_id}, owner={owner_id}")
        time.sleep(2)  # simulate heavy computation
        report_url = f"https://storage.example.com/reports/task_{task_id}.pdf"
        logger.info(f"[REPORT] Done: {report_url}")
        return {"status": "complete", "report_url": report_url, "task_id": task_id}
    except Exception as exc:
        logger.error(f"[REPORT] Failed: {exc}")
        raise self.retry(exc=exc)


@celery_app.task
def process_task_async(task_id: int, title: str):
    """
    Background processing triggered when a new task is created.
    Dispatches email alert + report generation.
    """
    send_email_alert.delay(
        recipient="owner@example.com",
        subject=f"New Task Created: {title}",
        body=f"Task ID {task_id} has been created and is pending.",
    )
    generate_report.delay(task_id=task_id, owner_id=0)
    return {"dispatched": True, "task_id": task_id}
