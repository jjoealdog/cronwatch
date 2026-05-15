"""Command-line interface for cronwatch."""

from __future__ import annotations

import argparse
import sys
from typing import Callable

from cronwatch.config import CronwatchConfig, load_config
from cronwatch.notifier import send_email_alert, log_alert
from cronwatch.scheduler import Scheduler
from cronwatch.tracker import JobTracker
from cronwatch.reporter import full_report


def _build_alert_fn(cfg: CronwatchConfig) -> Callable[[str, str], None]:
    def alert(job_name: str, reason: str) -> None:
        log_alert(job_name, reason)
        alert_cfg = cfg.alert
        if alert_cfg and alert_cfg.recipients:
            send_email_alert(alert_cfg, job_name, reason)

    return alert


def alert(args: argparse.Namespace) -> None:  # pragma: no cover
    cfg = load_config(args.config)
    fn = _build_alert_fn(cfg)
    fn(args.job, args.reason)


def report(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    tracker = JobTracker(state_file=cfg.state_file)
    history_dir = cfg.history_dir or ".cronwatch_history"
    print(full_report(cfg.jobs, tracker, history_dir))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cronwatch", description="Monitor cron jobs")
    parser.add_argument("-c", "--config", default="cronwatch.yaml", help="Config file path")
    sub = parser.add_subparsers(dest="command")

    run_p = sub.add_parser("run", help="Start the monitoring daemon")

    alert_p = sub.add_parser("alert", help="Send a manual alert")
    alert_p.add_argument("job", help="Job name")
    alert_p.add_argument("reason", help="Alert reason")

    sub.add_parser("report", help="Print a status report for all jobs")

    args = parser.parse_args(argv)

    if args.command == "run":  # pragma: no cover
        cfg = load_config(args.config)
        tracker = JobTracker(state_file=cfg.state_file)
        scheduler = Scheduler(cfg, tracker, _build_alert_fn(cfg))
        scheduler.start()
    elif args.command == "alert":
        alert(args)
    elif args.command == "report":
        report(args)
    else:
        parser.print_help()
        return 1

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
