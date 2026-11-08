#!/usr/bin/env python3
"""Entry point:  python main.py [--date YYYY-MM-DD] [--no-email]"""
import sys

from daily_report.cli import main

if __name__ == "__main__":
    sys.exit(main())
