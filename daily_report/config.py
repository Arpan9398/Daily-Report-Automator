"""Configuration loaded from environment variables (optionally a .env file)."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from .exceptions import ConfigError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def load_env() -> None:
    """Load .env from the project root (does not override real env vars)."""
    load_dotenv(PROJECT_ROOT / ".env", override=False)


def _resolve(path_str: str) -> Path:
    p = Path(path_str).expanduser()
    return p if p.is_absolute() else PROJECT_ROOT / p


@dataclass(frozen=True)
class ReportSettings:
    data_dir: Path
    output_dir: Path
    csv_pattern: str
    title: str
    trend_days: int

    @classmethod
    def from_env(cls) -> "ReportSettings":
        try:
            trend_days = int(os.getenv("TREND_DAYS", "7"))
        except ValueError as exc:
            raise ConfigError("TREND_DAYS must be an integer.") from exc
        return cls(
            data_dir=_resolve(os.getenv("DATA_DIR", "data/sample")),
            output_dir=_resolve(os.getenv("OUTPUT_DIR", "output")),
            csv_pattern=os.getenv("CSV_PATTERN", "sales_{date}.csv"),
            title=os.getenv("REPORT_TITLE", "Daily Sales Report"),
            trend_days=max(1, trend_days),
        )


@dataclass(frozen=True)
class EmailSettings:
    host: str
    port: int
    security: str  # starttls | ssl | none
    user: str
    password: str
    sender: str
    recipients: tuple[str, ...]

    REQUIRED = ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "EMAIL_FROM", "EMAIL_TO")

    @classmethod
    def from_env(cls) -> "EmailSettings":
        """Build settings or raise ConfigError listing everything that is wrong."""
        env = {k: (os.getenv(k) or "").strip() for k in cls.REQUIRED}
        missing = [k for k, v in env.items() if not v]
        if missing:
            raise ConfigError(
                "Missing email settings: " + ", ".join(missing) + ". "
                "Copy .env.example to .env and fill them in, or run with --no-email."
            )

        try:
            port = int(env["SMTP_PORT"])
        except ValueError as exc:
            raise ConfigError(f"SMTP_PORT must be a number, got {env['SMTP_PORT']!r}.") from exc

        security = (os.getenv("SMTP_SECURITY") or "starttls").strip().lower()
        if security not in {"starttls", "ssl", "none"}:
            raise ConfigError("SMTP_SECURITY must be one of: starttls, ssl, none.")

        recipients = tuple(r.strip() for r in env["EMAIL_TO"].split(",") if r.strip())
        bad = [a for a in (*recipients, env["EMAIL_FROM"]) if not _EMAIL_RE.match(a)]
        if bad:
            raise ConfigError("Invalid email address(es): " + ", ".join(bad))

        return cls(
            host=env["SMTP_HOST"],
            port=port,
            security=security,
            user=env["SMTP_USER"],
            password=env["SMTP_PASSWORD"],
            sender=env["EMAIL_FROM"],
            recipients=recipients,
        )
