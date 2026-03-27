# ============================================================
#  tests/test_parser.py
#  Unit tests for log_parser.parser
#  Built by Claude (claude.ai) · Anthropic
# ============================================================

import gzip


from log_parser.parser import LogEntry, _parse_bytes, _parse_line, parse_file, parse_stream
from tests.conftest import (
    BOT_LINE,
    EMPTY_LINE,
    ERROR_404_LINE,
    ERROR_500_LINE,
    MALFORMED_LINE,
    VALID_LINE,
    VALID_LINE_NO_REFERER_AGENT,
    WHITESPACE_LINE,
)


# ---------------------------------------------------------------------------
# _parse_bytes
# ---------------------------------------------------------------------------

class TestParseBytes:
    def test_numeric_string(self):
        assert _parse_bytes("2326") == 2326

    def test_zero(self):
        assert _parse_bytes("0") == 0

    def test_dash_returns_zero(self):
        assert _parse_bytes("-") == 0

    def test_empty_string_returns_zero(self):
        assert _parse_bytes("") == 0

    def test_large_value(self):
        assert _parse_bytes("1073741824") == 1_073_741_824


# ---------------------------------------------------------------------------
# _parse_line — valid lines
# ---------------------------------------------------------------------------

class TestParseLineValid:
    def test_returns_log_entry(self):
        entry = _parse_line(VALID_LINE)
        assert isinstance(entry, LogEntry)

    def test_ip(self):
        entry = _parse_line(VALID_LINE)
        assert entry.ip == "192.168.1.1"

    def test_user(self):
        entry = _parse_line(VALID_LINE)
        assert entry.user == "alice"

    def test_method(self):
        entry = _parse_line(VALID_LINE)
        assert entry.method == "GET"

    def test_path(self):
        entry = _parse_line(VALID_LINE)
        assert entry.path == "/index.html"

    def test_protocol(self):
        entry = _parse_line(VALID_LINE)
        assert entry.protocol == "HTTP/1.1"

    def test_status(self):
        entry = _parse_line(VALID_LINE)
        assert entry.status == 200

    def test_bytes_sent(self):
        entry = _parse_line(VALID_LINE)
        assert entry.bytes_sent == 2326

    def test_referer(self):
        entry = _parse_line(VALID_LINE)
        assert entry.referer == "https://example.com"

    def test_agent(self):
        entry = _parse_line(VALID_LINE)
        assert "Mozilla/5.0" in entry.agent

    def test_timestamp_year(self):
        entry = _parse_line(VALID_LINE)
        assert entry.timestamp.year == 2023

    def test_timestamp_month(self):
        entry = _parse_line(VALID_LINE)
        assert entry.timestamp.month == 10

    def test_timestamp_day(self):
        entry = _parse_line(VALID_LINE)
        assert entry.timestamp.day == 10

    def test_line_with_leading_whitespace(self):
        assert _parse_line("  " + VALID_LINE) is not None

    def test_line_without_referer_agent(self):
        entry = _parse_line(VALID_LINE_NO_REFERER_AGENT)
        assert entry is not None
        assert entry.status == 201
        assert entry.bytes_sent == 512


# ---------------------------------------------------------------------------
# _parse_line — invalid / edge-case lines
# ---------------------------------------------------------------------------

class TestParseLineInvalid:
    def test_malformed_returns_none(self):
        assert _parse_line(MALFORMED_LINE) is None

    def test_empty_string_returns_none(self):
        assert _parse_line(EMPTY_LINE) is None

    def test_whitespace_only_returns_none(self):
        assert _parse_line(WHITESPACE_LINE) is None

    def test_partial_line_returns_none(self):
        assert _parse_line('192.168.1.1 - - [bad-date] "GET / HTTP/1.1" 200 0') is None


# ---------------------------------------------------------------------------
# LogEntry properties
# ---------------------------------------------------------------------------

class TestLogEntryProperties:
    def test_status_class_2xx(self, sample_entry):
        assert sample_entry.status_class == "2xx"

    def test_status_class_4xx(self, error_entry):
        assert error_entry.status_class == "4xx"

    def test_is_error_false_for_200(self, sample_entry):
        assert sample_entry.is_error is False

    def test_is_error_true_for_404(self, error_entry):
        assert error_entry.is_error is True

    def test_is_server_error_false_for_404(self, error_entry):
        assert error_entry.is_server_error is False

    def test_is_server_error_true_for_500(self):
        entry = _parse_line(ERROR_500_LINE)
        assert entry.is_server_error is True

    def test_is_bot_false_for_human(self, sample_entry):
        assert sample_entry.is_bot is False

    def test_is_bot_true_for_googlebot(self, bot_entry):
        assert bot_entry.is_bot is True

    def test_is_bot_true_for_bingbot(self):
        entry = _parse_line(
            '1.2.3.4 - - [01/Jan/2024:00:00:00 +0000] '
            '"GET / HTTP/1.1" 200 100 "-" '
            '"Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)"'
        )
        assert entry.is_bot is True

    def test_is_bot_true_for_spider(self):
        entry = _parse_line(
            '1.2.3.4 - - [01/Jan/2024:00:00:00 +0000] '
            '"GET / HTTP/1.1" 200 100 "-" "generic-spider/1.0"'
        )
        assert entry.is_bot is True

    def test_bytes_dash_parsed_as_zero(self):
        line = (
            '1.1.1.1 - - [01/Jan/2024:00:00:00 +0000] '
            '"GET / HTTP/1.1" 304 - "-" "Mozilla/5.0"'
        )
        entry = _parse_line(line)
        assert entry is not None
        assert entry.bytes_sent == 0


# ---------------------------------------------------------------------------
# parse_file
# ---------------------------------------------------------------------------

class TestParseFile:
    def test_parses_plain_text_file(self, tmp_path):
        log = tmp_path / "access.log"
        log.write_text(VALID_LINE + "\n" + BOT_LINE + "\n", encoding="utf-8")
        entries, skipped = parse_file(log)
        assert len(entries) == 2
        assert skipped == 0

    def test_skips_malformed_lines(self, tmp_path):
        log = tmp_path / "access.log"
        log.write_text(
            VALID_LINE + "\n" + MALFORMED_LINE + "\n" + BOT_LINE + "\n",
            encoding="utf-8",
        )
        entries, skipped = parse_file(log)
        assert len(entries) == 2
        assert skipped == 1

    def test_blank_lines_not_counted_as_skipped(self, tmp_path):
        log = tmp_path / "access.log"
        log.write_text(VALID_LINE + "\n\n" + BOT_LINE + "\n", encoding="utf-8")
        entries, skipped = parse_file(log)
        assert skipped == 0

    def test_empty_file_returns_empty(self, tmp_path):
        log = tmp_path / "access.log"
        log.write_text("", encoding="utf-8")
        entries, skipped = parse_file(log)
        assert entries == []
        assert skipped == 0

    def test_parses_gzip_file(self, tmp_path):
        log = tmp_path / "access.log.gz"
        content = (VALID_LINE + "\n" + BOT_LINE + "\n").encode("utf-8")
        with gzip.open(log, "wb") as fh:
            fh.write(content)
        entries, skipped = parse_file(log)
        assert len(entries) == 2

    def test_accepts_path_string(self, tmp_path):
        log = tmp_path / "access.log"
        log.write_text(VALID_LINE + "\n", encoding="utf-8")
        entries, _ = parse_file(str(log))
        assert len(entries) == 1


# ---------------------------------------------------------------------------
# parse_stream
# ---------------------------------------------------------------------------

class TestParseStream:
    def test_yields_entries(self):
        lines = [VALID_LINE, BOT_LINE, ERROR_404_LINE]
        entries = list(parse_stream(iter(lines)))
        assert len(entries) == 3

    def test_skips_malformed_silently(self):
        lines = [VALID_LINE, MALFORMED_LINE, BOT_LINE]
        entries = list(parse_stream(iter(lines)))
        assert len(entries) == 2

    def test_empty_iterator_yields_nothing(self):
        entries = list(parse_stream(iter([])))
        assert entries == []
