# ============================================================
#  log_parser/cli.py
#  Click CLI — moved here so pyproject.toml can register
#  the `logparser` console script entry point.
#  Built by Claude (claude.ai) · Anthropic
# ============================================================

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

from . import __author__, __version__
from .analyzer import analyze, format_bytes
from .dashboard import render_dashboard
from .parser import parse_file, parse_stream

console = Console()
err_console = Console(stderr=True)


def _version_str() -> str:
    return f"LogParser v{__version__} · {__author__}"


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("logfile", metavar="LOGFILE|'-'")
@click.option("--top",         "-n", default=15,   show_default=True, help="Number of top entries to display per table.")
@click.option("--status",      "-s", default=None, type=int,           help="Filter: only show entries with this HTTP status code.")
@click.option("--method",      "-m", default=None,                     help="Filter: only show entries with this HTTP method (GET, POST ...).")
@click.option("--ip",                default=None,                     help="Filter: only analyse requests from this IP address.")
@click.option("--no-bots",           is_flag=True, default=False,      help="Exclude bot / crawler traffic from analysis.")
@click.option("--export-json",       default=None, metavar="FILE",     help="Export summary stats to a JSON file.")
@click.option("--version",     "-v", is_flag=True, default=False,      help="Show version and exit.")
def cli(logfile, top, status, method, ip, no_bots, export_json, version):
    """
    \b
    Apache / Nginx access log analyser
    Built by Claude (claude.ai · Anthropic)

    Analyse LOGFILE (use '-' to read from stdin).
    Supports plain text and .gz compressed log files.
    """
    if version:
        console.print(f"[bold cyan]{_version_str()}[/bold cyan]")
        raise SystemExit(0)

    # ── Load entries ──────────────────────────────────────────────────────────
    skipped = 0

    if logfile == "-":
        with Progress(SpinnerColumn(), TextColumn("[cyan]Reading stdin..."), console=err_console, transient=True) as p:
            p.add_task("read")
            entries = list(parse_stream(sys.stdin))
    else:
        path = Path(logfile)
        if not path.exists():
            err_console.print(f"[bold red]Error:[/bold red] File not found: {logfile}")
            raise SystemExit(1)

        size_str = format_bytes(path.stat().st_size)
        with Progress(
            SpinnerColumn(),
            TextColumn(f"[cyan]Parsing [bold]{path.name}[/bold] ({size_str})..."),
            BarColumn(),
            console=err_console,
            transient=True,
        ) as p:
            p.add_task("parse")
            entries, skipped = parse_file(path)

    if not entries:
        err_console.print("[bold red]No log entries found.[/bold red] Check the file format.")
        raise SystemExit(1)

    # ── Apply filters ─────────────────────────────────────────────────────────
    original_count = len(entries)

    if no_bots:
        entries = [e for e in entries if not e.is_bot]
    if status is not None:
        entries = [e for e in entries if e.status == status]
    if method:
        entries = [e for e in entries if e.method.upper() == method.upper()]
    if ip:
        entries = [e for e in entries if e.ip == ip]

    filtered_count = original_count - len(entries)
    if filtered_count:
        err_console.print(
            f"[dim]Filters removed {filtered_count:,} of {original_count:,} entries "
            f"({len(entries):,} remaining).[/dim]"
        )

    if not entries:
        err_console.print("[bold yellow]No entries match the applied filters.[/bold yellow]")
        raise SystemExit(0)

    # ── Analyse ───────────────────────────────────────────────────────────────
    with Progress(SpinnerColumn(), TextColumn("[cyan]Analysing..."), console=err_console, transient=True) as p:
        p.add_task("analyse")
        stats = analyze(entries, skipped=skipped)

    # ── Render ────────────────────────────────────────────────────────────────
    render_dashboard(stats, top_n=top)

    # ── JSON export ───────────────────────────────────────────────────────────
    if export_json:
        _export_json(stats, export_json)
        console.print(f"\n[bold green]OK[/bold green] Stats exported to [cyan]{export_json}[/cyan]")


def _export_json(stats, path: str) -> None:
    """Write a JSON summary of the stats."""
    data = {
        "meta": {
            "generated_by": "LogParser — Built by Claude (claude.ai · Anthropic)",
            "version": __version__,
        },
        "summary": {
            "total_requests": stats.total_requests,
            "unique_ips": stats.unique_ip_count,
            "unique_paths": stats.unique_path_count,
            "total_bytes": stats.total_bytes,
            "error_rate_pct": round(stats.error_rate, 2),
            "bot_rate_pct": round(stats.bot_rate, 2),
            "requests_per_second": round(stats.requests_per_second, 4),
            "skipped_lines": stats.skipped_lines,
            "first_request": stats.first_request.isoformat() if stats.first_request else None,
            "last_request": stats.last_request.isoformat() if stats.last_request else None,
        },
        "top_paths": dict(stats.top_paths.most_common(20)),
        "top_ips": dict(stats.top_ips.most_common(20)),
        "status_codes": {str(k): v for k, v in sorted(stats.status_codes.items())},
        "methods": dict(stats.methods.most_common()),
        "requests_by_hour": dict(sorted(stats.requests_by_hour.items())),
        "requests_by_day": dict(sorted(stats.requests_by_day.items())),
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
