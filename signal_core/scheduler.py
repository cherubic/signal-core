import logging
import sys
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv

from .pipeline import run_pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    load_dotenv()
    args = sys.argv[1:]

    if args and args[0] == "run":
        logger.info("Manual run triggered")
        run_pipeline()
        return

    scheduler = BlockingScheduler()
    scheduler.add_job(run_pipeline, "cron", hour=8, minute=0)
    logger.info("Scheduler started — pipeline runs daily at 08:00")
    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Scheduler stopped")
