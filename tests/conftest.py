# ============================================================
#  tests/conftest.py  —  shared fixtures
#  Built by Claude (claude.ai) · Anthropic
# ============================================================

import pytest
from datetime import datetime, timezone

from log_parser.parser import LogEntry

# ---------------------------------------------------------------------------
# Raw log line samples
# ---------------------------------------------------------------------------

VALID_LINE = (
    '192.168.1.1 - alice [10/Oct/2023:13:55:36 +0000] '
    '"GET /index.html HTTP/1.1" 200 2326 '
    '"https://example.com" "Mozilla/5.0 (Windows NT 10.0)"'
)

VALID_LINE_NO_REFERER_AGENT = (
    '10.0.0.1 - - [01/Jan/2024:00:00:00 +0000] '
    '"POST /api/data HTTP/1.1" 201 512'
)

BOT_LINE = (
    '66.249.66.1 - - [15/Mar/2024:08:00:00 +0000] '
    '"GET /robots.txt HTTP/1.1" 200 100 '
    '"-" "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"'
)

ERROR_404_LINE = (
    '203.0.113.5 - - [20/Feb/2024:12:00:00 +0000] '
    '"GET /missing.html HTTP/1.1" 404 512 "-" "curl/7.88.0"'
)

ERROR_500_LINE = (
    '203.0.113.5 - - [20/Feb/2024:12:01:00 +0000] '
    '"POST /api/crash HTTP/1.1" 500 0 "-" "python-requests/2.31.0"'
)

MALFORMED_LINE = "this is not a log line at all"
EMPTY_LINE = ""
WHITESPACE_LINE = "   \t  "

# ---------------------------------------------------------------------------
# Fixture: a minimal valid LogEntry
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_entry() -> LogEntry:
    return LogEntry(
        ip="192.168.1.1",
        user="alice",
        timestamp=datetime(2023, 10, 10, 13, 55, 36, tzinfo=timezone.utc),
        method="GET",
        path="/index.html",
        protocol="HTTP/1.1",
        status=200,
        bytes_sent=2326,
        referer="https://example.com",
        agent="Mozilla/5.0 (Windows NT 10.0)",
    )


@pytest.fixture
def bot_entry() -> LogEntry:
    return LogEntry(
        ip="66.249.66.1",
        user="-",
        timestamp=datetime(2024, 3, 15, 8, 0, 0, tzinfo=timezone.utc),
        method="GET",
        path="/robots.txt",
        protocol="HTTP/1.1",
        status=200,
        bytes_sent=100,
        referer="-",
        agent="Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    )


@pytest.fixture
def error_entry() -> LogEntry:
    return LogEntry(
        ip="203.0.113.5",
        user="-",
        timestamp=datetime(2024, 2, 20, 12, 0, 0, tzinfo=timezone.utc),
        method="GET",
        path="/missing.html",
        protocol="HTTP/1.1",
        status=404,
        bytes_sent=512,
        referer="-",
        agent="curl/7.88.0",
    )
