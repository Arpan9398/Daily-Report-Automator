"""Unit tests (stdlib unittest; also runs under pytest)."""
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import pandas as pd

from daily_report.cleaner import clean
from daily_report.config import EmailSettings
from daily_report.data_loader import load_csv
from daily_report.exceptions import ConfigError, InvalidCSVError
from daily_report.stats import compute_stats

HEADER = "order_id,date,region,product,category,quantity,unit_price,payment_method\n"


def write_csv(text: str) -> Path:
    f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8")
    f.write(text)
    f.close()
    return Path(f.name)


class LoaderTests(unittest.TestCase):
    def test_missing_file(self):
        with self.assertRaises(InvalidCSVError):
            load_csv("does_not_exist.csv")

    def test_empty_file(self):
        with self.assertRaises(InvalidCSVError):
            load_csv(write_csv(""))

    def test_missing_columns(self):
        with self.assertRaises(InvalidCSVError) as ctx:
            load_csv(write_csv("order_id,date\nA,2026-01-01\n"))
        self.assertIn("missing required column", str(ctx.exception))

    def test_header_only(self):
        with self.assertRaises(InvalidCSVError):
            load_csv(write_csv(HEADER))

    def test_valid(self):
        df = load_csv(write_csv(HEADER + "A1,2026-01-01,north,Pen,Stationery,2,5.0,Cash\n"))
        self.assertEqual(len(df), 1)


class CleanerTests(unittest.TestCase):
    def setUp(self):
        rows = [
            "A1,2026-01-01, north ,Pen,Stationery,2,5.00,Cash",
            "A1,2026-01-01, north ,Pen,Stationery,2,5.00,Cash",   # exact duplicate
            "A1,2026-01-01,north,Pen,Stationery,9,5.00,Cash",     # same order id
            "A2,2026-01-01,,Book,,1,10.00,",                      # missing categoricals
            "A3,2026-01-01,South,Book,Stationery,,10.00,Cash",    # missing quantity
            "A4,2026-01-01,South,Book,Stationery,abc,10.00,Cash", # invalid quantity
            "A5,2026-01-01,South,Book,Stationery,-1,10.00,Cash",  # negative quantity
            ",,,,,,,",                                            # blank row
        ]
        self.raw = load_csv(write_csv(HEADER + "\n".join(rows) + "\n"))

    def test_clean(self):
        df, rep = clean(self.raw)
        self.assertEqual(list(df["order_id"]), ["A1", "A2"])
        self.assertEqual(rep.duplicates_removed, 2)
        self.assertEqual(rep.empty_rows_removed, 1)
        self.assertEqual(rep.missing_key_fields_removed, 1)
        self.assertEqual(rep.invalid_values_removed, 2)
        self.assertEqual(df.loc[0, "region"], "North")
        self.assertEqual(df.loc[1, "region"], "Unknown")
        self.assertEqual(df.loc[1, "payment_method"], "Unknown")
        self.assertEqual(rep.rows_final, 2)

    def test_all_invalid_raises(self):
        raw = load_csv(write_csv(HEADER + "A1,2026-01-01,N,P,C,x,1,Cash\n"))
        with self.assertRaises(InvalidCSVError):
            clean(raw)


class StatsTests(unittest.TestCase):
    def test_kpis(self):
        raw = load_csv(write_csv(
            HEADER
            + "A1,2026-01-01,North,Pen,Stationery,2,5.00,Cash\n"
            + "A2,2026-01-01,South,Book,Stationery,1,10.00,UPI\n"
            + "A3,2026-01-01,North,Pen,Stationery,3,5.00,Cash\n"
        ))
        df, _ = clean(raw)
        s = compute_stats(df, date(2026, 1, 1))
        self.assertEqual(s.kpis["Total revenue"], 35.0)
        self.assertEqual(s.kpis["Total orders"], 3)
        self.assertEqual(s.kpis["Total units sold"], 6)
        self.assertAlmostEqual(s.kpis["Average order value"], 11.67, places=2)
        self.assertEqual(s.kpis["Top region"], "North")
        self.assertEqual(int(s.by_region.loc[0, "orders"]), 2)


class EmailConfigTests(unittest.TestCase):
    def test_missing_settings(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ConfigError) as ctx:
                EmailSettings.from_env()
        self.assertIn("SMTP_HOST", str(ctx.exception))

    def test_valid_settings(self):
        env = {
            "SMTP_HOST": "smtp.example.com", "SMTP_PORT": "587", "SMTP_USER": "u",
            "SMTP_PASSWORD": "p", "EMAIL_FROM": "a@example.com", "EMAIL_TO": "b@example.com, c@example.com",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            s = EmailSettings.from_env()
        self.assertEqual(s.recipients, ("b@example.com", "c@example.com"))
        self.assertEqual(s.security, "starttls")

    def test_bad_port_and_address(self):
        env = {
            "SMTP_HOST": "h", "SMTP_PORT": "abc", "SMTP_USER": "u",
            "SMTP_PASSWORD": "p", "EMAIL_FROM": "a@example.com", "EMAIL_TO": "b@example.com",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ConfigError):
                EmailSettings.from_env()
        env.update(SMTP_PORT="587", EMAIL_TO="not-an-email")
        with mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ConfigError):
                EmailSettings.from_env()


if __name__ == "__main__":
    unittest.main()
