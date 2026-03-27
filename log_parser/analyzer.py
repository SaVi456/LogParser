# ============================================================
#  log_parser/analyzer.py
#  Statistical analysis of parsed log entries
#  Built by Claude (claude.ai) · Anthropic
# ============================================================

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .parser import LogEntry


@dataclass
class Stats:
    # ── Totals ──────────────────────────────────────────────
    total_requests: int = 0
    total_bytes: int = 0
    skipped_lines: int = 0

    # ── Time window ─────────────────────────────────────────
    first_request: Optional[datetime] = None
    last_request: Optional[datetime] = None

    # ── Unique counts ────────────────────────────────────────
    unique_ips: set = field(default_factory=set)
    unique_paths: set = field(default_factory=set)

    # ── Counters ─────────────────────────────────────────────
    status_codes: Counter = field(default_factory=Counter)
    methods: Counter = field(default_factory=Counter)
    top_ips: Counter = field(default_factory=Counter)
    top_paths: Counter = field(default_factory=Counter)
    top_agents: Counter = field(default_factory=Counter)
    top_referers: Counter = field(default_factory=Counter)

    # ── Hourly / daily traffic ───────────────────────────────
    requests_by_hour: Counter = field(default_factory=Counter)   # "HH" key
    requests_by_day: Counter = field(default_factory=Counter)    # "YYYY-MM-DD" key

    # ── Bots ─────────────────────────────────────────────────
    bot_requests: int = 0
    human_requests: int = 0

    # ── Errors ───────────────────────────────────────────────
    recent_errors: list = field(default_factory=list)  # last 20 error entries
    error_paths: Counter = field(default_factory=Counter)

    # ── Bandwidth per path ───────────────────────────────────
    bytes_by_path: Counter = field(default_factory=Counter)

    # ── Derived properties ───────────────────────────────────
    @property
    def error_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        errors = sum(v for k, v in self.status_codes.items() if k >= 400)
        return errors / self.total_requests * 100

    @property
    def bot_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.bot_requests / self.total_requests * 100

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.first_request and self.last_request:
            delta = self.last_request - self.first_request
            return delta.total_seconds()
        return None

    @property
    def requests_per_second(self) -> float:
        secs = self.duration_seconds
        if secs and secs > 0:
            return self.total_requests / secs
        return 0.0

    @property
    def avg_response_size(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_bytes / self.total_requests

    @property
    def status_class_counts(self) -> dict[str, int]:
        classes: dict[str, int] = defaultdict(int)
        for code, count in self.status_codes.items():
            classes[f"{code // 100}xx"] += count
        return dict(classes)

    @property
    def unique_ip_count(self) -> int:
        return len(self.unique_ips)

    @property
    def unique_path_count(self) -> int:
        return len(self.unique_paths)


def analyze(entries: list[LogEntry], skipped: int = 0) -> Stats:
    """Crunch all parsed log entries into a Stats summary."""
    s = Stats(skipped_lines=skipped)

    for e in entries:
        s.total_requests += 1
        s.total_bytes += e.bytes_sent

        # Time window
        if s.first_request is None or e.timestamp < s.first_request:
            s.first_request = e.timestamp
        if s.last_request is None or e.timestamp > s.last_request:
            s.last_request = e.timestamp

        # Uniques
        s.unique_ips.add(e.ip)
        s.unique_paths.add(e.path)

        # Counters
        s.status_codes[e.status] += 1
        s.methods[e.method] += 1
        s.top_ips[e.ip] += 1
        s.top_paths[e.path] += 1
        s.bytes_by_path[e.path] += e.bytes_sent

        if e.agent and e.agent != "-":
            s.top_agents[e.agent] += 1
        if e.referer and e.referer not in ("-", ""):
            s.top_referers[e.referer] += 1

        # Time buckets
        hour_key = e.timestamp.strftime("%H:00")
        s.requests_by_hour[hour_key] += 1
        day_key = e.timestamp.strftime("%Y-%m-%d")
        s.requests_by_day[day_key] += 1

        # Bots
        if e.is_bot:
            s.bot_requests += 1
        else:
            s.human_requests += 1

        # Errors
        if e.is_error:
            s.error_paths[e.path] += 1
            if len(s.recent_errors) < 20:
                s.recent_errors.append(e)

    return s


def format_bytes(n: int) -> str:
    """Human-readable byte count."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"
