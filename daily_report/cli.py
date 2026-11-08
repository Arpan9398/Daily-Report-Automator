"""Command line interface.

Exit codes: 0 success | 1 unexpected error | 2 invalid/missing CSV | 3 email/config error
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime
from pathlib import Path

from .config import EmailSettings, ReportSettings, load_env
from .exceptions import DailyReportError
from .pipeline import build_report, email_report

log = logging.getLogger("daily_report")


def _parse_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid date {value!r}; use YYYY-MM-DD.") from exc


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="daily-report", description="Generate and email the daily Excel report.")
    p.add_argument("--date", type=_parse_date, default=None, help="Report date YYYY-MM-DD (default: today)")
    p.add_argument("--csv", type=Path, default=None, help="Explicit CSV path (overrides DATA_DIR/CSV_PATTERN)")
    p.add_argument("--no-email", action="store_true", help="Build the Excel report but do not send it")
    p.add_argument("-v", "--verbose", action="store_true", help="Debug logging")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    load_env()

    report_date = args.date or date.today()
    try:
        settings = ReportSettings.from_env()
        result = build_report(settings, report_date, args.csv)
    except DailyReportError as exc:
        log.error("%s", exc)
        return exc.exit_code
    except Exception:  # noqa: BLE001 - last-resort handler for cron logs
        log.exception("Unexpected error while building the report")
        return 1

    print(f"Report saved: {result.excel_path}")

    if args.no_email:
        log.info("--no-email given: skipping email step")
        return 0

    try:
        email_settings = EmailSettings.from_env()
        email_report(result, settings, email_settings)
    except DailyReportError as exc:
        log.error("%s", exc)
        log.error("The report was still saved at %s", result.excel_path)
        return exc.exit_code
    except Exception:  # noqa: BLE001
        log.exception("Unexpected error while sending the email")
        return 1

    print("Email sent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
