"""Cleaning: missing values, duplicates, bad numbers, whitespace."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .exceptions import InvalidCSVError

TEXT_FILL = "Unknown"
# Words that must stay upper-case when normalising capitalisation (extend as needed).
ACRONYMS = {"upi", "usa", "uk", "eu", "emi", "cod", "atm"}


def _title(value: str) -> str:
    return " ".join(w.upper() if w.lower() in ACRONYMS else w.capitalize() for w in value.split())


@dataclass
class CleaningReport:
    rows_loaded: int = 0
    empty_rows_removed: int = 0
    duplicates_removed: int = 0
    missing_key_fields_removed: int = 0
    invalid_values_removed: int = 0
    missing_values_filled: dict[str, int] = field(default_factory=dict)
    rows_final: int = 0

    @property
    def rows_removed(self) -> int:
        return self.rows_loaded - self.rows_final

    def as_rows(self) -> list[tuple[str, int]]:
        rows = [
            ("Rows loaded", self.rows_loaded),
            ("Completely empty rows removed", self.empty_rows_removed),
            ("Duplicate rows removed", self.duplicates_removed),
            ("Rows missing order ID/date/quantity/price removed", self.missing_key_fields_removed),
            ("Rows with invalid values removed", self.invalid_values_removed),
        ]
        rows += [(f"Missing '{k}' filled with '{TEXT_FILL}'", v) for k, v in self.missing_values_filled.items()]
        rows.append(("Rows in final dataset", self.rows_final))
        return rows


def clean(raw: pd.DataFrame) -> tuple[pd.DataFrame, CleaningReport]:
    """Return (clean_df, report). `raw` must be all-string columns from load_csv."""
    report = CleaningReport(rows_loaded=len(raw))
    df = raw.copy()

    # 1. Trim whitespace; blank strings become missing.
    for col in df.columns:
        df[col] = df[col].astype("object").map(lambda v: v.strip() if isinstance(v, str) else v)
        df[col] = df[col].replace("", pd.NA)

    # 2. Drop completely empty rows.
    before = len(df)
    df = df.dropna(how="all")
    report.empty_rows_removed = before - len(df)

    # 3. Drop exact duplicate rows.
    before = len(df)
    df = df.drop_duplicates()
    report.duplicates_removed += before - len(df)

    # 4. Drop rows missing fields the statistics cannot work without.
    key = ["order_id", "date", "quantity", "unit_price"]
    before = len(df)
    df = df.dropna(subset=key)
    report.missing_key_fields_removed = before - len(df)

    # 5. Convert types; drop rows that cannot be converted or make no sense.
    before = len(df)
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    valid = (
        df["quantity"].notna()
        & df["unit_price"].notna()
        & df["date"].notna()
        & (df["quantity"] > 0)
        & (df["unit_price"] >= 0)
    )
    df = df[valid].copy()
    report.invalid_values_removed = before - len(df)

    # 6. Same order ID appearing twice (even with different values): keep the first.
    before = len(df)
    df = df.drop_duplicates(subset=["order_id"], keep="first")
    report.duplicates_removed += before - len(df)

    # 7. Fill missing categorical values and normalise capitalisation.
    for col in ["region", "product", "category", "payment_method"]:
        n = int(df[col].isna().sum())
        if n:
            report.missing_values_filled[col] = n
        df[col] = df[col].fillna(TEXT_FILL)
    for col in ["region", "category", "payment_method"]:
        df[col] = df[col].astype(str).map(_title)
    df["product"] = df["product"].astype(str)

    df["quantity"] = df["quantity"].round().astype(int)
    df["unit_price"] = df["unit_price"].astype(float)
    df["revenue"] = (df["quantity"] * df["unit_price"]).round(2)
    df["date"] = df["date"].dt.date

    df = df.reset_index(drop=True)
    report.rows_final = len(df)

    if df.empty:
        raise InvalidCSVError("No valid rows left after cleaning - check the CSV contents.")
    return df, report
