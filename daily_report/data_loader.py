"""Reading and validating CSV files."""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from .exceptions import InvalidCSVError

REQUIRED_COLUMNS = [
    "order_id",
    "date",
    "region",
    "product",
    "category",
    "quantity",
    "unit_price",
    "payment_method",
]


def csv_path_for(data_dir: Path, pattern: str, report_date: date) -> Path:
    return data_dir / pattern.format(date=report_date.isoformat())


def load_csv(path: str | Path) -> pd.DataFrame:
    """Load a CSV as raw strings; raise InvalidCSVError with a clear message on any problem."""
    path = Path(path)
    if not path.exists():
        raise InvalidCSVError(f"CSV file not found: {path}")
    if not path.is_file() or path.suffix.lower() != ".csv":
        raise InvalidCSVError(f"Not a .csv file: {path}")
    if path.stat().st_size == 0:
        raise InvalidCSVError(f"CSV file is empty: {path}")

    try:
        df = pd.read_csv(path, dtype=str, encoding="utf-8-sig", skipinitialspace=True)
    except pd.errors.EmptyDataError as exc:
        raise InvalidCSVError(f"CSV file has no data: {path}") from exc
    except pd.errors.ParserError as exc:
        raise InvalidCSVError(f"CSV file is malformed ({path.name}): {exc}") from exc
    except UnicodeDecodeError as exc:
        raise InvalidCSVError(f"CSV file is not valid UTF-8 text: {path.name}") from exc
    except OSError as exc:
        raise InvalidCSVError(f"Could not read {path}: {exc}") from exc

    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise InvalidCSVError(
            f"{path.name} is missing required column(s): {', '.join(missing)}. "
            f"Expected: {', '.join(REQUIRED_COLUMNS)}"
        )
    if df.empty:
        raise InvalidCSVError(f"{path.name} has a header but no data rows.")

    return df[REQUIRED_COLUMNS]


def load_history(data_dir: Path, pattern: str, end_date: date, days: int) -> list[tuple[date, Path]]:
    """Return existing (date, path) pairs for the `days` days up to and including end_date."""
    found = []
    for offset in range(days - 1, -1, -1):
        d = end_date - timedelta(days=offset)
        p = csv_path_for(data_dir, pattern, d)
        if p.exists():
            found.append((d, p))
    return found
