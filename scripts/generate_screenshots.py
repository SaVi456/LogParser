#!/usr/bin/env python3
"""
Generate SVG screenshots of the LogParser dashboard for the README.
Built by Claude (claude.ai) · Anthropic
"""

from pathlib import Path
import sys

# Make sure the package root is on the path when run directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from log_parser.parser import parse_file
from log_parser.analyzer import analyze
from log_parser import dashboard as _dashboard_module

OUT_DIR = Path(__file__).parent.parent / "docs" / "img"
OUT_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = Path(__file__).parent.parent / "sample_logs" / "access.log"


def _make_recording_console(width: int = 110) -> Console:
    return Console(record=True, width=width, force_terminal=True, force_jupyter=False)


def capture_full_dashboard():
    print("Capturing full dashboard...")
    entries, skipped = parse_file(LOG_FILE)
    stats = analyze(entries, skipped=skipped)

    # Swap the module-level console for a recording one
    rec = _make_recording_console(width=120)
    original = _dashboard_module.console
    _dashboard_module.console = rec

    try:
        _dashboard_module.render_dashboard(stats, top_n=10)
    finally:
        _dashboard_module.console = original

    out = OUT_DIR / "dashboard.svg"
    rec.save_svg(str(out), title="LogParser — Built by Claude")
    print(f"  Saved {out}")


def capture_help():
    print("Capturing --help output...")
    from click.testing import CliRunner
    from log_parser.cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["--help"], color=True)

    rec = _make_recording_console(width=90)
    rec.print(result.output)

    out = OUT_DIR / "help.svg"
    rec.save_svg(str(out), title="logparser --help")
    print(f"  Saved {out}")


def capture_filtered():
    print("Capturing --status 404 filtered view...")
    entries, skipped = parse_file(LOG_FILE)
    error_entries = [e for e in entries if e.status == 404]
    stats = analyze(error_entries, skipped=0)

    rec = _make_recording_console(width=110)
    original = _dashboard_module.console
    _dashboard_module.console = rec
    try:
        _dashboard_module.render_dashboard(stats, top_n=8)
    finally:
        _dashboard_module.console = original

    out = OUT_DIR / "filtered_404.svg"
    rec.save_svg(str(out), title="logparser access.log --status 404")
    print(f"  Saved {out}")


if __name__ == "__main__":
    capture_full_dashboard()
    capture_help()
    capture_filtered()
    print("\nDone. Images saved to docs/img/")
