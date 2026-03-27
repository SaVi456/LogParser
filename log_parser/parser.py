# ============================================================
#  log_parser/parser.py
#  Apache / Nginx Combined Log Format parser
#  Built by Claude (claude.ai) · Anthropic
# ============================================================

from __future__ import annotations

import re
import gzip
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

# Apache Combined Log Format
# 127.0.0.1 - frank [10/Oct/2000:13:55:36 -0700] "GET /index.html HTTP/1.1" 200 2326 "-" "Mozilla/5.0"
_COMBINED_LOG_RE = re.compile(
    r'(?P<ip>\S+)'           # Remote host
    r'\s+\S+'                # Ident (ignored)
    r'\s+(?P<user>\S+)'      # Auth user
    r'\s+\[(?P<time>[^\]]+)\]'  # Time
    r'\s+"(?P<method>\S+)\s+(?P<path>\S+)\s+(?P<protocol>[^"]+)"'  # Request
    r'\s+(?P<status>\d{3})'  # Status code
    r'\s+(?P<bytes>\S+)'     # Bytes sent
    r'(?:\s+"(?P<referer>[^"]*)")?'    # Referer (optional)
    r'(?:\s+"(?P<agent>[^"]*)")?'      # User-agent (optional)
)

_TIME_FORMAT = "%d/%b/%Y:%H:%M:%S %z"

# Common bot / crawler signatures
_BOT_PATTERNS = re.compile(
    r"bot|crawler|spider|slurp|baiduspider|googlebot|bingbot|yandex",
    re.IGNORECASE,
)


@dataclass(slots=True)
class LogEntry:
    ip: str
    user: str
    timestamp: datetime
    method: str
    path: str
    protocol: str
    status: int
    bytes_sent: int
    referer: str
    agent: str
    is_bot: bool = field(init=False)

    def __post_init__(self) -> None:
        self.is_bot = bool(_BOT_PATTERNS.search(self.agent))

    @property
    def status_class(self) -> str:
        """Return HTTP status class: 2xx, 3xx, 4xx, 5xx."""
        return f"{self.status // 100}xx"

    @property
    def is_error(self) -> bool:
        return self.status >= 400

    @property
    def is_server_error(self) -> bool:
        return self.status >= 500


def _parse_bytes(raw: str) -> int:
    """Parse bytes field — handles '-' (no body)."""
    return int(raw) if raw.isdigit() else 0


def _parse_time(raw: str) -> datetime:
    return datetime.strptime(raw, _TIME_FORMAT)


def _parse_line(line: str) -> Optional[LogEntry]:
    """Parse a single log line. Returns None on parse failure."""
    line = line.strip()
    if not line:
        return None
    m = _COMBINED_LOG_RE.match(line)
    if not m:
        return None
    try:
        return LogEntry(
            ip=m.group("ip"),
            user=m.group("user"),
            timestamp=_parse_time(m.group("time")),
            method=m.group("method"),
            path=m.group("path"),
            protocol=m.group("protocol"),
            status=int(m.group("status")),
            bytes_sent=_parse_bytes(m.group("bytes")),
            referer=m.group("referer") or "-",
            agent=m.group("agent") or "-",
        )
    except (ValueError, TypeError):
        return None


def parse_file(path: str | Path) -> tuple[list[LogEntry], int]:
    """
    Parse a log file (plain text or .gz).

    Returns:
        (entries, skipped_lines) — skipped_lines counts unparseable rows.
    """
    path = Path(path)
    entries: list[LogEntry] = []
    skipped = 0

    opener = gzip.open if path.suffix == ".gz" else open

    with opener(path, "rt", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            entry = _parse_line(line)
            if entry is not None:
                entries.append(entry)
            else:
                if line.strip():   # don't count blank lines
                    skipped += 1

    return entries, skipped


def parse_stream(lines: Iterator[str]) -> Iterator[LogEntry]:
    """Parse log entries from an arbitrary iterable of lines (e.g. stdin)."""
    for line in lines:
        entry = _parse_line(line)
        if entry is not None:
            yield entry
