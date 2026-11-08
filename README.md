# Daily Report Automator

Turns a daily sales CSV into a formatted Excel report and emails it - automatically.

**Pipeline:** CSV -> clean (missing values, duplicates, bad rows) -> statistics -> Matplotlib charts -> Excel workbook (OpenPyXL) -> email (SMTP)

**Stack:** Python 3.10+, Pandas, Matplotlib, OpenPyXL, `smtplib`, python-dotenv

## What you get

The Excel workbook (`output/<date>/daily_report_<date>.xlsx`) contains:

| Sheet | Contents |
|---|---|
| **Summary** | Key metrics (revenue, orders, units, averages, median, top region/product) and breakdowns by region, product, category and payment method |
| **Charts** | Revenue by region, top 5 products, category share, and a 7-day revenue trend (when history files exist) |
| **Data Quality** | How many rows were loaded, removed (empty / duplicate / invalid) and how many values were filled |
| **Cleaned Data** | The final dataset with filters and a frozen header |

## Project structure

```
daily-report-automator/
├── main.py                    # entry point
├── daily_report/
│   ├── cli.py                 # arguments, logging, exit codes
│   ├── config.py              # .env / environment settings + validation
│   ├── data_loader.py         # CSV reading and validation
│   ├── cleaner.py             # missing values, duplicates, invalid rows
│   ├── stats.py               # totals, averages, counts, breakdowns
│   ├── charts.py              # Matplotlib charts (PNG)
│   ├── excel_report.py        # formatted workbook
│   ├── emailer.py             # SMTP sending
│   ├── pipeline.py            # ties the steps together
│   └── exceptions.py
├── data/sample/               # 7 days of messy sample CSVs (2026-11-02 .. 2026-11-08)
├── data/invalid_examples/     # broken CSVs for testing error handling
├── scripts/                   # generate_sample_data.py, run_daily.sh (cron wrapper)
├── cron/crontab.example
├── .github/workflows/daily-report.yml
├── tests/
├── requirements.txt           # runtime dependencies
├── requirements-dev.txt       # + pytest
└── .env.example
```

## Setup

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure email (skip if you only want the Excel file)
cp .env.example .env               # Windows: copy .env.example .env
# then edit .env with your SMTP details
```

### Email settings (`.env`)

| Variable | Description |
|---|---|
| `SMTP_HOST`, `SMTP_PORT` | Server and port, e.g. `smtp.gmail.com` / `587` |
| `SMTP_SECURITY` | `starttls` (port 587, default), `ssl` (port 465) or `none` (local test servers only) |
| `SMTP_USER`, `SMTP_PASSWORD` | Login. Gmail/Outlook require an **app password** (needs 2-step verification) |
| `EMAIL_FROM` | Sender address |
| `EMAIL_TO` | Recipients, comma-separated |

Optional: `DATA_DIR` (default `data/sample`), `OUTPUT_DIR`, `CSV_PATTERN` (default `sales_{date}.csv`), `REPORT_TITLE`, `TREND_DAYS`.

## Running

```bash
# Build the report from the sample data, no email
python main.py --date 2026-11-08 --no-email

# Build and email today's report (expects data/sample/sales_<today>.csv)
python main.py

# A specific day
python main.py --date 2026-11-05

# A CSV from anywhere
python main.py --csv /path/to/my_file.csv --date 2026-11-08 --no-email

# Debug logging
python main.py -v --no-email
```

`python -m daily_report ...` works too.

### Using your own data

Put one CSV per day in `DATA_DIR`, named to match `CSV_PATTERN` (default `sales_YYYY-MM-DD.csv`), with these columns (names are case-insensitive; spaces become underscores):

`order_id, date, region, product, category, quantity, unit_price, payment_method`

Revenue is calculated as `quantity x unit_price`. To use different columns, adjust `REQUIRED_COLUMNS` in `data_loader.py` and the aggregations in `stats.py`.

### Cleaning rules

1. Whitespace is trimmed; blank strings count as missing.
2. Completely empty rows and exact duplicate rows are removed.
3. Rows missing `order_id`, `date`, `quantity` or `unit_price` are removed.
4. Rows with non-numeric values, quantity <= 0, negative price or an unparseable date are removed.
5. A repeated `order_id` keeps only the first row.
6. Missing `region`, `product`, `category` or `payment_method` are filled with `Unknown`.
7. Text is normalised (`" north "` becomes `North`).

Everything removed or filled is reported on the **Data Quality** sheet.

## Error handling and exit codes

| Exit code | Meaning |
|---|---|
| `0` | Success |
| `1` | Unexpected error (full traceback logged) |
| `2` | Invalid CSV: file not found, empty, malformed, not UTF-8, missing required columns, header only, or no valid rows after cleaning |
| `3` | Email problem: missing/invalid SMTP settings, login failed, server unreachable, recipients refused |

If email fails, the Excel report is **still saved** and its path is logged. Try the error paths yourself:

```bash
python main.py --csv data/invalid_examples/missing_columns.csv --no-email   # exit 2
python main.py --date 2026-11-08                                            # exit 3 if .env is not configured
```

## Scheduling

### Option A - cron (Linux/macOS server)

1. Make sure `.venv` and `.env` are set up on the server.
2. `crontab -e` and add (adjust the path):

```cron
30 7 * * 1-5 /absolute/path/to/daily-report-automator/scripts/run_daily.sh
```

`scripts/run_daily.sh` activates the virtualenv and appends output to `logs/daily_report.log`. See `cron/crontab.example` for more schedules. Your daily CSV must exist in `DATA_DIR` before the job runs.

### Option B - GitHub Actions

`.github/workflows/daily-report.yml` runs on a schedule (default weekdays 02:00 **UTC**) and can also be started manually from the Actions tab (with optional date and a "send email" switch).

1. Push the project to GitHub (`.env` is git-ignored, so credentials never get committed).
2. Go to **Settings -> Secrets and variables -> Actions -> Secrets** and add: `SMTP_HOST`, `SMTP_PORT`, `SMTP_SECURITY`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_FROM`, `EMAIL_TO`.
3. Optionally add a repository **variable** `DATA_DIR` if your CSVs live elsewhere in the repo.
4. The workflow reads CSVs committed to the repository. If your data lives elsewhere (S3, an API, a shared drive), add a step before "Build and email report" to download it into `DATA_DIR`.
5. The generated Excel file and charts are uploaded as a workflow artifact (kept 14 days).

Note: scheduled workflows run on the default branch and can be delayed by several minutes at busy times.

## Tests

```bash
python -m unittest discover -s tests -v
# or: pip install -r requirements-dev.txt && pytest
```

Regenerate the sample data any time with `python scripts/generate_sample_data.py`.

## Security notes

- Never commit `.env`; only `.env.example` (placeholders) is shipped.
- Use app passwords or a dedicated SMTP account, and prefer `starttls`/`ssl`.
- In GitHub Actions, credentials live in encrypted Secrets, never in the workflow file.

## Troubleshooting

| Problem | Fix |
|---|---|
| `CSV file not found` | Check the date, `DATA_DIR` and `CSV_PATTERN` |
| `missing required column(s)` | Make sure the header matches the columns listed above |
| `SMTP login failed` | Use an app password; confirm host/port/security match your provider |
| Cron job does nothing | Check `logs/daily_report.log`; use absolute paths; ensure `run_daily.sh` is executable (`chmod +x`) |
