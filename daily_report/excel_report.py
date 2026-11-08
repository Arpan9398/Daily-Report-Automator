"""Formatted Excel workbook: Summary, Charts, Data Quality, Cleaned Data."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from .cleaner import CleaningReport
from .stats import ReportStats

NAVY = "1F4E79"
LIGHT = "DCE6F1"
HEADER_FONT = Font(bold=True, color="FFFFFF")
HEADER_FILL = PatternFill("solid", fgColor=NAVY)
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
MONEY = '#,##0.00'
INT = '#,##0'

_MONEY_KPIS = {"Total revenue", "Average order value", "Median order value", "Largest order"}
_INT_KPIS = {"Total orders", "Total units sold", "Unique products", "Regions covered"}


def _header(ws, row: int, col: int, labels: list[str]) -> None:
    for i, label in enumerate(labels):
        c = ws.cell(row=row, column=col + i, value=label)
        c.font, c.fill, c.border = HEADER_FONT, HEADER_FILL, BORDER
        c.alignment = Alignment(horizontal="center", vertical="center")


def _section(ws, row: int, title: str) -> None:
    c = ws.cell(row=row, column=1, value=title)
    c.font = Font(bold=True, size=12, color=NAVY)


def _write_breakdown(ws, start_row: int, title: str, df: pd.DataFrame, label: str) -> int:
    """Write a breakdown table; return the next free row."""
    _section(ws, start_row, title)
    _header(ws, start_row + 1, 1, [label, "Orders", "Units", "Revenue", "Share %"])
    r = start_row + 2
    for rec in df.itertuples(index=False):
        values = [rec[0], rec.orders, rec.units, rec.revenue, rec.share_pct / 100]
        formats = [None, INT, INT, MONEY, "0.0%"]
        for j, (v, f) in enumerate(zip(values, formats), start=1):
            c = ws.cell(row=r, column=j, value=v.item() if hasattr(v, "item") else v)
            c.border = BORDER
            if f:
                c.number_format = f
        r += 1
    return r + 1


def _fit_to_page(ws, landscape: bool = False) -> None:
    """Print-friendly: one page wide."""
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.page_setup.orientation = "landscape" if landscape else "portrait"


def _build_summary(wb: Workbook, title: str, stats: ReportStats) -> None:
    ws = wb.active
    ws.title = "Summary"
    ws.sheet_view.showGridLines = False

    ws.merge_cells("A1:E1")
    ws["A1"] = f"{title} - {stats.kpis['Report date']}"
    ws["A1"].font = Font(bold=True, size=16, color="FFFFFF")
    ws["A1"].fill = HEADER_FILL
    ws["A1"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[1].height = 30

    _section(ws, 3, "Key Metrics")
    _header(ws, 4, 1, ["Metric", "Value"])
    r = 5
    for k, v in stats.kpis.items():
        a = ws.cell(row=r, column=1, value=k)
        b = ws.cell(row=r, column=2, value=v)
        a.border = b.border = BORDER
        a.fill = PatternFill("solid", fgColor=LIGHT)
        b.alignment = Alignment(horizontal="right")
        if k in _MONEY_KPIS:
            b.number_format = MONEY
        elif k in _INT_KPIS:
            b.number_format = INT
        r += 1

    r += 1
    r = _write_breakdown(ws, r, "Revenue by Region", stats.by_region, "Region")
    r = _write_breakdown(ws, r, "Revenue by Product", stats.by_product, "Product")
    r = _write_breakdown(ws, r, "Revenue by Category", stats.by_category, "Category")
    _write_breakdown(ws, r, "Revenue by Payment Method", stats.by_payment, "Payment method")

    for col, width in zip("ABCDE", (30, 18, 12, 16, 12)):
        ws.column_dimensions[col].width = width
    _fit_to_page(ws)


def _build_charts(wb: Workbook, charts: list[Path]) -> None:
    ws = wb.create_sheet("Charts")
    ws.sheet_view.showGridLines = False
    ws["A1"] = "Charts"
    ws["A1"].font = Font(bold=True, size=16, color=NAVY)
    # 2-column grid; each image is about 700x400 px (~ 13 columns x 21 rows).
    for i, path in enumerate(charts):
        img = XLImage(str(path))
        img.width, img.height = 560, 320
        col = "A" if i % 2 == 0 else "K"
        row = 3 + (i // 2) * 18
        ws.add_image(img, f"{col}{row}")
    _fit_to_page(ws, landscape=True)


def _build_quality(wb: Workbook, report: CleaningReport) -> None:
    ws = wb.create_sheet("Data Quality")
    ws.sheet_view.showGridLines = False
    _header(ws, 1, 1, ["Check", "Count"])
    for i, (label, n) in enumerate(report.as_rows(), start=2):
        a, b = ws.cell(row=i, column=1, value=label), ws.cell(row=i, column=2, value=n)
        a.border = b.border = BORDER
        b.number_format = INT
    ws.column_dimensions["A"].width = 58
    ws.column_dimensions["B"].width = 12


def _build_data(wb: Workbook, df: pd.DataFrame) -> None:
    ws = wb.create_sheet("Cleaned Data")
    cols = ["order_id", "date", "region", "product", "category", "quantity", "unit_price", "revenue", "payment_method"]
    _header(ws, 1, 1, [c.replace("_", " ").title() for c in cols])
    for r, rec in enumerate(df[cols].itertuples(index=False), start=2):
        for c, v in enumerate(rec, start=1):
            cell = ws.cell(row=r, column=c, value=v.item() if hasattr(v, "item") else v)
            if cols[c - 1] == "date":
                cell.number_format = "yyyy-mm-dd"
            elif cols[c - 1] in ("unit_price", "revenue"):
                cell.number_format = MONEY
    ws.freeze_panes = "A2"
    ws.print_title_rows = "1:1"
    _fit_to_page(ws, landscape=True)
    ws.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{len(df) + 1}"
    for i, c in enumerate(cols, start=1):
        longest = max([len(str(c))] + [len(str(x)) for x in df[c].head(500)])
        ws.column_dimensions[get_column_letter(i)].width = min(longest + 4, 34)


def build_workbook(
    path: Path,
    title: str,
    df: pd.DataFrame,
    stats: ReportStats,
    report: CleaningReport,
    charts: list[Path],
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    _build_summary(wb, title, stats)
    _build_charts(wb, charts)
    _build_quality(wb, report)
    _build_data(wb, df)
    wb.save(path)
    return path
