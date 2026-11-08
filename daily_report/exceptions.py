"""Custom exceptions so the CLI can give clear messages and exit codes."""


class DailyReportError(Exception):
    """Base class for all expected errors."""

    exit_code = 1


class InvalidCSVError(DailyReportError):
    """The CSV is missing, empty, malformed or lacks required columns."""

    exit_code = 2


class ConfigError(DailyReportError):
    """Required configuration (e.g. SMTP settings) is missing or invalid."""

    exit_code = 3


class EmailError(DailyReportError):
    """Sending the email failed."""

    exit_code = 3
