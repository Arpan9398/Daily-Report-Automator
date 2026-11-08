"""Matplotlib charts saved as PNG files."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: works in cron / CI with no display
import matplotlib.pyplot as plt  # noqa: E402

from .stats import ReportStats  # noqa: E402

PALETTE = ["#1F4E79", "#2E86C1", "#5DADE2", "#F39C12", "#27AE60", "#8E44AD", "#C0392B", "#7F8C8D"]
FIGSIZE = (7, 4)
DPI = 100


def _save(fig, path: Path) -> Path:
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    return path


def _region_chart(stats: ReportStats, out: Path) -> Path:
    d = stats.by_region
    fig, ax = plt.subplots(figsize=FIGSIZE)
    bars = ax.bar(d["region"], d["revenue"], color=PALETTE[: len(d)])
    ax.bar_label(bars, labels=[f"{v:,.0f}" for v in d["revenue"]], padding=3, fontsize=8)
    ax.set_title("Revenue by Region", fontweight="bold")
    ax.set_ylabel("Revenue")
    ax.spines[["top", "right"]].set_visible(False)
    return _save(fig, out / "revenue_by_region.png")


def _product_chart(stats: ReportStats, out: Path) -> Path:
    d = stats.by_product.head(5).iloc[::-1]
    fig, ax = plt.subplots(figsize=FIGSIZE)
    bars = ax.barh(d["product"], d["revenue"], color=PALETTE[1])
    ax.bar_label(bars, labels=[f"{v:,.0f}" for v in d["revenue"]], padding=3, fontsize=8)
    ax.set_title("Top 5 Products by Revenue", fontweight="bold")
    ax.set_xlabel("Revenue")
    ax.spines[["top", "right"]].set_visible(False)
    return _save(fig, out / "top_products.png")


def _category_chart(stats: ReportStats, out: Path) -> Path:
    d = stats.by_category
    fig, ax = plt.subplots(figsize=FIGSIZE)
    wedges, _, autotexts = ax.pie(
        d["revenue"],
        autopct=lambda p: f"{p:.0f}%" if p >= 4 else "",
        startangle=90,
        colors=PALETTE[: len(d)],
        pctdistance=0.75,
        wedgeprops={"edgecolor": "white"},
    )
    for t in autotexts:
        t.set_color("white")
        t.set_fontsize(9)
    ax.legend(wedges, [f"{c} ({v:,.0f})" for c, v in zip(d["category"], d["revenue"])],
              loc="center left", bbox_to_anchor=(1.0, 0.5), frameon=False)
    ax.set_title("Revenue Share by Category", fontweight="bold")
    return _save(fig, out / "category_share.png")


def _trend_chart(stats: ReportStats, out: Path) -> Path:
    d = stats.trend
    fig, ax = plt.subplots(figsize=FIGSIZE)
    labels = [x.strftime("%b %d") for x in d["date"]]
    ax.plot(labels, d["revenue"], marker="o", color=PALETTE[0], linewidth=2)
    ax.fill_between(labels, d["revenue"], alpha=0.12, color=PALETTE[0])
    ax.set_title(f"Revenue Trend (last {len(d)} days)", fontweight="bold")
    ax.set_ylabel("Revenue")
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)
    return _save(fig, out / "revenue_trend.png")


def generate_charts(stats: ReportStats, out_dir: Path) -> list[Path]:
    """Create all charts; the trend chart only when at least 2 days of history exist."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = [_region_chart(stats, out_dir), _product_chart(stats, out_dir), _category_chart(stats, out_dir)]
    if len(stats.trend) >= 2:
        paths.append(_trend_chart(stats, out_dir))
    return paths
