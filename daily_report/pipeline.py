"""Orchestrates the whole run."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from .charts import generate_charts
from .cleaner import CleaningReport, clean
from .config import EmailSettings, ReportSettings
from .data_loader import csv_path_for, load_csv, load_history
from .emailer import send_report, summary_text
from .excel_report import build_workbook
from .exceptions import DailyReportError, InvalidCSVError
from .stats import ReportStats, compute_stats

log = logging.getLogger(__name__)


@dataclass
class RunResult:
    excel_path: Path
    stats: ReportStats
    cleaning: CleaningReport
    emailed: bool = False


def _build_trend(settings: ReportSettings, report_date: date, today_df: pd.DataFrame) -> pd.DataFrame:
    """Daily revenue for recent days. Unreadable history files are skipped with a warning."""
    rows = []
    for d, path in load_history(settings.data_dir, settings.csv_pattern, report_date, settings.trend_days):
        try:
            df = today_df if d == report_date else clean(load_csv(path))[0]
        except DailyReportError as exc:
            log.warning("Skipping %s in trend: %s", path.name, exc)
            continue
        rows.append({"date": d, "revenue": float(df["revenue"].sum()), "orders": int(df["order_id"].nunique())})
    return pd.DataFrame(rows, columns=["date", "revenue", "orders"])


def build_report(settings: ReportSettings, report_date: date, csv_file: Path | None = None) -> RunResult:
    """Load -> clean -> stats -> charts -> Excel. No email."""
    path = csv_file or csv_path_for(settings.data_dir, settings.csv_pattern, report_date)
    log.info("Reading %s", path)
    raw = load_csv(path)
    df, cleaning = clean(raw)
    log.info("Cleaned: %d -> %d rows", cleaning.rows_loaded, cleaning.rows_final)

    trend = _build_trend(settings, report_date, df) if csv_file is None else None
    stats = compute_stats(df, report_date, trend)

    out_dir = settings.output_dir / report_date.isoformat()
    charts = generate_charts(stats, out_dir / "charts")
    excel_path = build_workbook(
        out_dir / f"daily_report_{report_date.isoformat()}.xlsx", settings.title, df, stats, cleaning, charts
    )
    log.info("Excel report written to %s", excel_path)
    return RunResult(excel_path=excel_path, stats=stats, cleaning=cleaning)


def email_report(result: RunResult, settings: ReportSettings, email_settings: EmailSettings) -> None:
    kpis = result.stats.kpis
    subject = f"{settings.title} - {kpis['Report date']}"
    send_report(email_settings, subject, summary_text(settings.title, kpis), result.excel_path)
    result.emailed = True


__all__ = ["build_report", "email_report", "RunResult", "InvalidCSVError"]
