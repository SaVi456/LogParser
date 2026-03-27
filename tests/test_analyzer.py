# ============================================================
#  tests/test_analyzer.py
#  Unit tests for log_parser.analyzer
#  Built by Claude (claude.ai) · Anthropic
# ============================================================

import pytest
from datetime import datetime, timedelta, timezone

from log_parser.analyzer import Stats, analyze, format_bytes
from log_parser.parser import LogEntry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entry(
    ip="1.2.3.4",
    path="/",
    method="GET",
    status=200,
    bytes_sent=1000,
    agent="Mozilla/5.0",
    hour=12,
    day=1,
) -> LogEntry:
    return LogEntry(
        ip=ip,
        user="-",
        timestamp=datetime(2024, 1, day, hour, 0, 0, tzinfo=timezone.utc),
        method=method,
        path=path,
        protocol="HTTP/1.1",
        status=status,
        bytes_sent=bytes_sent,
        referer="-",
        agent=agent,
    )


# ---------------------------------------------------------------------------
# format_bytes
# ---------------------------------------------------------------------------

class TestFormatBytes:
    def test_bytes(self):
        assert format_bytes(512) == "512.0 B"

    def test_kilobytes(self):
        assert format_bytes(2048) == "2.0 KB"

    def test_megabytes(self):
        assert format_bytes(1024 * 1024) == "1.0 MB"

    def test_gigabytes(self):
        assert format_bytes(1024 ** 3) == "1.0 GB"

    def test_zero(self):
        assert format_bytes(0) == "0.0 B"


# ---------------------------------------------------------------------------
# analyze — basic counts
# ---------------------------------------------------------------------------

class TestAnalyzeBasic:
    def test_total_requests(self):
        entries = [_make_entry() for _ in range(5)]
        stats = analyze(entries)
        assert stats.total_requests == 5

    def test_empty_entries(self):
        stats = analyze([])
        assert stats.total_requests == 0

    def test_total_bytes(self):
        entries = [_make_entry(bytes_sent=500) for _ in range(4)]
        stats = analyze(entries)
        assert stats.total_bytes == 2000

    def test_skipped_lines_stored(self):
        stats = analyze([], skipped=7)
        assert stats.skipped_lines == 7

    def test_unique_ips(self):
        entries = [
            _make_entry(ip="1.1.1.1"),
            _make_entry(ip="2.2.2.2"),
            _make_entry(ip="1.1.1.1"),  # duplicate
        ]
        stats = analyze(entries)
        assert stats.unique_ip_count == 2

    def test_unique_paths(self):
        entries = [
            _make_entry(path="/a"),
            _make_entry(path="/b"),
            _make_entry(path="/a"),  # duplicate
        ]
        stats = analyze(entries)
        assert stats.unique_path_count == 2


# ---------------------------------------------------------------------------
# analyze — time window
# ---------------------------------------------------------------------------

class TestAnalyzeTimeWindow:
    def test_first_request(self):
        entries = [
            _make_entry(hour=10),
            _make_entry(hour=14),
            _make_entry(hour=8),
        ]
        stats = analyze(entries)
        assert stats.first_request.hour == 8

    def test_last_request(self):
        entries = [
            _make_entry(hour=10),
            _make_entry(hour=14),
            _make_entry(hour=8),
        ]
        stats = analyze(entries)
        assert stats.last_request.hour == 14

    def test_duration_seconds(self):
        base = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        e1 = _make_entry(hour=0)
        e2 = LogEntry(
            ip="1.2.3.4", user="-",
            timestamp=base + timedelta(hours=2),
            method="GET", path="/", protocol="HTTP/1.1",
            status=200, bytes_sent=0, referer="-", agent="Mozilla/5.0",
        )
        stats = analyze([e1, e2])
        assert stats.duration_seconds == pytest.approx(7200.0)

    def test_single_entry_duration_is_zero(self):
        stats = analyze([_make_entry()])
        assert stats.duration_seconds == 0.0

    def test_no_entries_duration_is_none(self):
        stats = analyze([])
        assert stats.duration_seconds is None


# ---------------------------------------------------------------------------
# analyze — counters
# ---------------------------------------------------------------------------

class TestAnalyzeCounters:
    def test_status_code_counted(self):
        entries = [_make_entry(status=200), _make_entry(status=404), _make_entry(status=200)]
        stats = analyze(entries)
        assert stats.status_codes[200] == 2
        assert stats.status_codes[404] == 1

    def test_methods_counted(self):
        entries = [
            _make_entry(method="GET"),
            _make_entry(method="POST"),
            _make_entry(method="GET"),
        ]
        stats = analyze(entries)
        assert stats.methods["GET"] == 2
        assert stats.methods["POST"] == 1

    def test_top_paths_counted(self):
        entries = [
            _make_entry(path="/a"),
            _make_entry(path="/b"),
            _make_entry(path="/a"),
        ]
        stats = analyze(entries)
        assert stats.top_paths["/a"] == 2
        assert stats.top_paths["/b"] == 1

    def test_top_ips_counted(self):
        entries = [
            _make_entry(ip="1.1.1.1"),
            _make_entry(ip="1.1.1.1"),
            _make_entry(ip="2.2.2.2"),
        ]
        stats = analyze(entries)
        assert stats.top_ips["1.1.1.1"] == 2

    def test_bytes_by_path(self):
        entries = [
            _make_entry(path="/img", bytes_sent=5000),
            _make_entry(path="/img", bytes_sent=3000),
            _make_entry(path="/api", bytes_sent=200),
        ]
        stats = analyze(entries)
        assert stats.bytes_by_path["/img"] == 8000
        assert stats.bytes_by_path["/api"] == 200

    def test_hourly_bucket(self):
        entries = [_make_entry(hour=9), _make_entry(hour=9), _make_entry(hour=14)]
        stats = analyze(entries)
        assert stats.requests_by_hour["09:00"] == 2
        assert stats.requests_by_hour["14:00"] == 1

    def test_daily_bucket(self):
        entries = [_make_entry(day=1), _make_entry(day=1), _make_entry(day=2)]
        stats = analyze(entries)
        assert stats.requests_by_day["2024-01-01"] == 2
        assert stats.requests_by_day["2024-01-02"] == 1

    def test_referer_dash_not_counted(self):
        entries = [_make_entry()]  # referer="-"
        stats = analyze(entries)
        assert len(stats.top_referers) == 0

    def test_referer_counted_when_present(self):
        entry = LogEntry(
            ip="1.2.3.4", user="-",
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            method="GET", path="/", protocol="HTTP/1.1",
            status=200, bytes_sent=0,
            referer="https://google.com",
            agent="Mozilla/5.0",
        )
        stats = analyze([entry])
        assert stats.top_referers["https://google.com"] == 1


# ---------------------------------------------------------------------------
# analyze — bots
# ---------------------------------------------------------------------------

class TestAnalyzeBots:
    def test_bot_counted(self):
        bot = _make_entry(agent="Googlebot/2.1")
        stats = analyze([bot])
        assert stats.bot_requests == 1
        assert stats.human_requests == 0

    def test_human_counted(self):
        human = _make_entry(agent="Mozilla/5.0 (Windows NT 10.0)")
        stats = analyze([human])
        assert stats.human_requests == 1
        assert stats.bot_requests == 0

    def test_mixed_bot_human(self):
        entries = [
            _make_entry(agent="Googlebot/2.1"),
            _make_entry(agent="Mozilla/5.0"),
            _make_entry(agent="Mozilla/5.0"),
        ]
        stats = analyze(entries)
        assert stats.bot_requests == 1
        assert stats.human_requests == 2


# ---------------------------------------------------------------------------
# analyze — errors
# ---------------------------------------------------------------------------

class TestAnalyzeErrors:
    def test_error_paths_counted(self):
        entries = [
            _make_entry(path="/missing", status=404),
            _make_entry(path="/missing", status=404),
            _make_entry(path="/ok", status=200),
        ]
        stats = analyze(entries)
        assert stats.error_paths["/missing"] == 2
        assert "/ok" not in stats.error_paths

    def test_recent_errors_populated(self):
        entries = [_make_entry(status=500) for _ in range(5)]
        stats = analyze(entries)
        assert len(stats.recent_errors) == 5

    def test_recent_errors_capped_at_20(self):
        entries = [_make_entry(status=500) for _ in range(30)]
        stats = analyze(entries)
        assert len(stats.recent_errors) == 20

    def test_200_not_in_recent_errors(self):
        entries = [_make_entry(status=200) for _ in range(5)]
        stats = analyze(entries)
        assert len(stats.recent_errors) == 0


# ---------------------------------------------------------------------------
# Stats — derived properties
# ---------------------------------------------------------------------------

class TestStatsDerivedProperties:
    def test_error_rate_zero_when_no_errors(self):
        entries = [_make_entry(status=200) for _ in range(10)]
        stats = analyze(entries)
        assert stats.error_rate == 0.0

    def test_error_rate_100_when_all_errors(self):
        entries = [_make_entry(status=500) for _ in range(10)]
        stats = analyze(entries)
        assert stats.error_rate == 100.0

    def test_error_rate_partial(self):
        entries = [_make_entry(status=200)] * 3 + [_make_entry(status=404)]
        stats = analyze(entries)
        assert stats.error_rate == pytest.approx(25.0)

    def test_error_rate_zero_when_no_requests(self):
        stats = analyze([])
        assert stats.error_rate == 0.0

    def test_bot_rate(self):
        entries = [
            _make_entry(agent="Googlebot/2.1"),
            _make_entry(agent="Mozilla/5.0"),
            _make_entry(agent="Mozilla/5.0"),
            _make_entry(agent="Mozilla/5.0"),
        ]
        stats = analyze(entries)
        assert stats.bot_rate == pytest.approx(25.0)

    def test_avg_response_size(self):
        entries = [_make_entry(bytes_sent=1000), _make_entry(bytes_sent=3000)]
        stats = analyze(entries)
        assert stats.avg_response_size == pytest.approx(2000.0)

    def test_avg_response_size_zero_when_no_requests(self):
        stats = analyze([])
        assert stats.avg_response_size == 0.0

    def test_status_class_counts(self):
        entries = [
            _make_entry(status=200),
            _make_entry(status=201),
            _make_entry(status=404),
            _make_entry(status=500),
        ]
        stats = analyze(entries)
        counts = stats.status_class_counts
        assert counts["2xx"] == 2
        assert counts["4xx"] == 1
        assert counts["5xx"] == 1

    def test_requests_per_second_zero_for_single_entry(self):
        stats = analyze([_make_entry()])
        assert stats.requests_per_second == 0.0

    def test_requests_per_second_zero_for_empty(self):
        stats = analyze([])
        assert stats.requests_per_second == 0.0
