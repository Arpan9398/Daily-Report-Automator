"""Key statistics: totals, averages, counts and breakdowns."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd


@dataclass
class ReportStats:
    kpis: dict[str, float | int | str]
    by_region: pd.DataFrame
    by_product: pd.DataFrame
    by_category: pd.DataFrame
    by_payment: pd.DataFrame
    trend: pd.DataFrame = field(default_factory=lambda: pd.DataFrame(columns=["date", "revenue", "orders"]))


def _breakdown(df: pd.DataFrame, column: str) -> pd.DataFrame:
    out = (
        df.groupby(column)
        .agg(orders=("order_id", "count"), units=("quantity", "sum"), revenue=("revenue", "sum"))
        .sort_values("revenue", ascending=False)
        .reset_index()
    )
    total = out["revenue"].sum()
    out["share_pct"] = (out["revenue"] / total * 100).round(1) if total else 0.0
    out["revenue"] = out["revenue"].round(2)
    return out


def compute_stats(df: pd.DataFrame, report_date: date, trend: pd.DataFrame | None = None) -> ReportStats:
    orders = int(df["order_id"].nunique())
    total_revenue = float(df["revenue"].sum())
    kpis = {
        "Report date": report_date.isoformat(),
        "Total revenue": round(total_revenue, 2),
        "Total orders": orders,
        "Total units sold": int(df["quantity"].sum()),
        "Average order value": round(total_revenue / orders, 2),
        "Average units per order": round(float(df["quantity"].mean()), 2),
        "Median order value": round(float(df["revenue"].median()), 2),
        "Largest order": round(float(df["revenue"].max()), 2),
        "Unique products": int(df["product"].nunique()),
        "Regions covered": int(df.loc[df["region"] != "Unknown", "region"].nunique()),
    }
    by_region = _breakdown(df, "region")
    by_product = _breakdown(df, "product")
    kpis["Top region"] = str(by_region.iloc[0]["region"])
    kpis["Top product"] = str(by_product.iloc[0]["product"])

    return ReportStats(
        kpis=kpis,
        by_region=by_region,
        by_product=by_product,
        by_category=_breakdown(df, "category"),
        by_payment=_breakdown(df, "payment_method"),
        trend=trend if trend is not None else pd.DataFrame(columns=["date", "revenue", "orders"]),
    )
