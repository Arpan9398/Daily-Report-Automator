#!/usr/bin/env python3
"""Generate 7 days of messy sample sales CSVs in data/sample (deterministic)."""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "sample"
START = date(2026, 11, 2)
DAYS = 7

CATALOG = {
    "Laptop": ("Electronics", 899.0), "Smartphone": ("Electronics", 599.0),
    "Headphones": ("Electronics", 129.0), "Office Chair": ("Furniture", 189.0),
    "Standing Desk": ("Furniture", 349.0), "Notebook Pack": ("Stationery", 12.5),
    "Pen Set": ("Stationery", 8.75), "Coffee Beans 1kg": ("Grocery", 19.9),
}
REGIONS = ["North", "South", "East", "West"]
PAYMENTS = ["Credit Card", "UPI", "Cash", "Bank Transfer"]


def make_day(day: date, seed: int) -> list[list[str]]:
    rnd = random.Random(seed)
    rows = []
    for i in range(1, rnd.randint(55, 75) + 1):
        product = rnd.choice(list(CATALOG))
        category, price = CATALOG[product]
        rows.append([
            f"ORD-{day:%m%d}-{i:03d}", day.isoformat(), rnd.choice(REGIONS), product, category,
            str(rnd.randint(1, 5)), f"{price * rnd.uniform(0.95, 1.05):.2f}", rnd.choice(PAYMENTS),
        ])
    # --- inject typical data problems ---
    for _ in range(3):
        rows.append(list(rnd.choice(rows)))                      # exact duplicates
    dup = list(rnd.choice(rows[:20])); dup[5] = "9"; rows.append(dup)  # same order id, different qty
    for _ in range(3):
        rows[rnd.randrange(len(rows))][2] = ""                   # missing region
    for _ in range(2):
        rows[rnd.randrange(len(rows))][7] = ""                   # missing payment method
    rows[rnd.randrange(len(rows))][5] = ""                       # missing quantity
    rows[rnd.randrange(len(rows))][6] = "N/A"                    # bad price
    rows[rnd.randrange(len(rows))][5] = "-2"                     # negative quantity
    r = rows[rnd.randrange(len(rows))]; r[2] = "  north "; r[3] = f" {r[3]}  "  # whitespace / case
    rows.append([""] * 8)                                        # blank row
    rnd.shuffle(rows)
    return rows


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for n in range(DAYS):
        day = START + timedelta(days=n)
        path = OUT / f"sales_{day.isoformat()}.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["order_id", "date", "region", "product", "category", "quantity", "unit_price", "payment_method"])
            w.writerows(make_day(day, seed=100 + n))
        print("wrote", path)


if __name__ == "__main__":
    main()
