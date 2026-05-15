"""Command-line entry point for cronwatch daemon."""

import argparse
import logging
import sys

from cronwatch.config import load_config
from cronwatch.notifier import log_alert, send_email_alert
from cronwatch.scheduler import Scheduler
from cronwatch.tracker import JobTracker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("cronwatch")


def _build_alert_fn(config):
    """Return a composite alert function that logs and optionally emails."""

    def alert(job_name: str, reason: str, alert_cfg) -> None:
        log_alert(job_name, reason, alert_cfg)
        if alert_cfg and alert_cfg.recipients:
            send_email_alert(job_name, reason, alert_cfg)

    return alert


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="cronwatch — monitor cron job execution"
    )
    parser.add_argument("-c", "--config", default="cronwatch.yaml", help="Config file path")
    parser.add_argument("-s", "--state", default="/var/lib/cronwatch/state.json", help="State file path")
    parser.add_argument("--tick", type=int, default=60, help="Check interval in seconds")
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
    except FileNotFoundError:
        logger.error("Config file not found: %s", args.config)
        sys.exit(1)

    tracker = JobTracker(state_file=args.state)
    alert_fn = _build_alert_fn(config)
    scheduler = Scheduler(config, tracker, alert_fn, tick_seconds=args.tick)

    logger.info("Starting cronwatch with %d job(s)", len(config.jobs))
    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Shutting down")
        scheduler.stop()


if __name__ == "__main__":
    main()
