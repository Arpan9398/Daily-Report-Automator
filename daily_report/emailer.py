"""Send the report via SMTP."""
from __future__ import annotations

import logging
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

from .config import EmailSettings
from .exceptions import EmailError

log = logging.getLogger(__name__)
XLSX_MIME = ("application", "vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def build_message(settings: EmailSettings, subject: str, body_text: str, attachment: Path) -> EmailMessage:
    if not attachment.exists():
        raise EmailError(f"Attachment not found: {attachment}")
    msg = EmailMessage()
    msg["From"] = settings.sender
    msg["To"] = ", ".join(settings.recipients)
    msg["Subject"] = subject
    msg.set_content(body_text)
    msg.add_attachment(attachment.read_bytes(), maintype=XLSX_MIME[0], subtype=XLSX_MIME[1], filename=attachment.name)
    return msg


def send_report(settings: EmailSettings, subject: str, body_text: str, attachment: Path, timeout: int = 30) -> None:
    """Send the email; every failure becomes a readable EmailError."""
    msg = build_message(settings, subject, body_text, attachment)
    context = ssl.create_default_context()
    try:
        if settings.security == "ssl":
            server = smtplib.SMTP_SSL(settings.host, settings.port, timeout=timeout, context=context)
        else:
            server = smtplib.SMTP(settings.host, settings.port, timeout=timeout)
        with server:
            if settings.security == "starttls":
                server.starttls(context=context)
            server.login(settings.user, settings.password)
            server.send_message(msg)
    except smtplib.SMTPAuthenticationError as exc:
        raise EmailError("SMTP login failed - check SMTP_USER / SMTP_PASSWORD (use an app password for Gmail).") from exc
    except smtplib.SMTPRecipientsRefused as exc:
        raise EmailError(f"Recipients refused by the server: {exc}") from exc
    except (smtplib.SMTPException, OSError) as exc:
        raise EmailError(f"Could not send email via {settings.host}:{settings.port}: {exc}") from exc
    log.info("Email sent to %s", ", ".join(settings.recipients))


def summary_text(title: str, kpis: dict) -> str:
    lines = [f"{title} - {kpis['Report date']}", "", "Highlights:"]
    for key in ("Total revenue", "Total orders", "Total units sold", "Average order value", "Top region", "Top product"):
        v = kpis[key]
        lines.append(f"  - {key}: {v:,.2f}" if isinstance(v, float) else f"  - {key}: {v:,}" if isinstance(v, int) else f"  - {key}: {v}")
    lines += ["", "The full Excel report (summary, charts, data quality, cleaned data) is attached.", "", "-- Sent automatically by Daily Report Automator"]
    return "\n".join(lines)
