"""APScheduler jobs: calendar poll (every 15 min) + reminder check (hourly),
per backend/CLAUDE.md. In-process scheduler chosen as the simplest option for
a hackathon-scale build; swap for Celery + Redis (see infra/docker-compose.yml
`celery` profile) if the team needs a real job queue later.
"""
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import get_settings
from app.services.calendar_scanner import scan_tenant
from app.services.reminder_engine import run_due_sessions

logger = logging.getLogger(__name__)

_scheduler = AsyncIOScheduler()


async def _poll_all_tenants() -> None:
    for tenant_id in get_settings().tenant_oauth_configs:
        try:
            await scan_tenant(tenant_id)
        except Exception:
            # One tenant's failure must not affect the other's scheduled jobs.
            logger.exception("Calendar scan failed for tenant %s", tenant_id)


def start_scheduler() -> None:
    _scheduler.add_job(_poll_all_tenants, "interval", minutes=15, id="calendar_poll")
    _scheduler.add_job(run_due_sessions, "interval", hours=1, id="reminder_check")
    _scheduler.start()


def stop_scheduler() -> None:
    _scheduler.shutdown(wait=False)
