# ============================================================
#  log_parser/dashboard.py
#  Rich terminal dashboard renderer
#  Built by Claude (claude.ai) · Anthropic
# ============================================================

from __future__ import annotations

from datetime import datetime

from rich import box
from rich.align import Align
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import print as rprint

from .analyzer import Stats, format_bytes

import io
import sys

# Force UTF-8 output on Windows so Unicode characters render correctly
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

console = Console(file=sys.stdout)

# ── Colour palette ───────────────────────────────────────────────────────────
_STATUS_COLOURS = {
    "2xx": "bright_green",
    "3xx": "bright_cyan",
    "4xx": "bright_yellow",
    "5xx": "bright_red",
}
_METHOD_COLOURS = {
    "GET": "bright_green",
    "POST": "bright_blue",
    "PUT": "bright_yellow",
    "PATCH": "bright_yellow",
    "DELETE": "bright_red",
    "HEAD": "dim",
    "OPTIONS": "dim",
}


# ── Helper renderers ─────────────────────────────────────────────────────────

def _sparkbar(value: int, max_value: int, width: int = 20) -> str:
    """Simple ASCII bar proportional to value/max_value."""
    if max_value == 0:
        return " " * width
    filled = round(value / max_value * width)
    return "█" * filled + "░" * (width - filled)


def _header_panel() -> Panel:
    lines = Text(justify="center")
    lines.append("\n")
    lines.append("  ██╗      ██████╗  ██████╗ ██████╗  █████╗ ██████╗ ███████╗███████╗██████╗  \n", style="bold cyan")
    lines.append("  ██║     ██╔═══██╗██╔════╝ ██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔════╝██╔══██╗ \n", style="bold cyan")
    lines.append("  ██║     ██║   ██║██║  ███╗██████╔╝███████║██████╔╝███████╗█████╗  ██████╔╝ \n", style="bold cyan")
    lines.append("  ██║     ██║   ██║██║   ██║██╔═══╝ ██╔══██║██╔══██╗╚════██║██╔══╝  ██╔══██╗ \n", style="bold cyan")
    lines.append("  ███████╗╚██████╔╝╚██████╔╝██║     ██║  ██║██║  ██║███████║███████╗██║  ██║ \n", style="bold cyan")
    lines.append("  ╚══════╝ ╚═════╝  ╚═════╝ ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═╝ \n", style="bold cyan")
    lines.append("\n")
    lines.append("  Apache / Nginx Log Analyser  ·  ", style="dim")
    lines.append("Built by Claude", style="bold magenta")
    lines.append("  (claude.ai · Anthropic)\n", style="dim")
    return Panel(lines, border_style="cyan", padding=(0, 2))


def _summary_panels(s: Stats) -> Columns:
    def stat_panel(title: str, value: str, subtitle: str = "", colour: str = "white") -> Panel:
        body = Text(justify="center")
        body.append(f"\n{value}\n", style=f"bold {colour}")
        if subtitle:
            body.append(subtitle, style="dim")
        return Panel(body, title=f"[bold]{title}[/bold]", border_style=colour, padding=(0, 1))

    duration_str = ""
    if s.first_request and s.last_request:
        duration_str = (
            f"{s.first_request:%Y-%m-%d} → {s.last_request:%Y-%m-%d}"
        )

    panels = [
        stat_panel("Total Requests",  f"{s.total_requests:,}",    duration_str,                        "bright_cyan"),
        stat_panel("Unique IPs",       f"{s.unique_ip_count:,}",   f"{s.bot_rate:.1f}% bots",           "bright_blue"),
        stat_panel("Bandwidth",        format_bytes(s.total_bytes), f"avg {format_bytes(int(s.avg_response_size))}/req", "bright_green"),
        stat_panel("Error Rate",       f"{s.error_rate:.1f}%",     f"{s.unique_path_count:,} unique paths", "bright_red" if s.error_rate > 5 else "bright_yellow"),
        stat_panel("Req / sec",        f"{s.requests_per_second:.2f}", "", "magenta"),
    ]
    return Columns(panels, equal=True, expand=True)


def _top_paths_table(s: Stats, n: int = 15) -> Table:
    table = Table(
        title="[bold]Top Endpoints[/bold]",
        box=box.SIMPLE_HEAD,
        show_lines=False,
        border_style="cyan",
        header_style="bold cyan",
    )
    table.add_column("#",       style="dim",          width=4,  justify="right")
    table.add_column("Path",    style="white",        ratio=3,  no_wrap=True, overflow="fold")
    table.add_column("Requests", justify="right",     width=10)
    table.add_column("Bandwidth", justify="right",    width=11)
    table.add_column("Bar",     style="bright_green", ratio=1)

    top = s.top_paths.most_common(n)
    max_count = top[0][1] if top else 1
    for i, (path, count) in enumerate(top, 1):
        bw = format_bytes(s.bytes_by_path.get(path, 0))
        bar = _sparkbar(count, max_count, width=18)
        table.add_row(str(i), path, f"{count:,}", bw, f"[bright_green]{bar}[/bright_green]")
    return table


def _top_ips_table(s: Stats, n: int = 10) -> Table:
    table = Table(
        title="[bold]Top IP Addresses[/bold]",
        box=box.SIMPLE_HEAD,
        show_lines=False,
        border_style="blue",
        header_style="bold blue",
    )
    table.add_column("#",       style="dim",         width=4,  justify="right")
    table.add_column("IP Address", style="white",    width=18)
    table.add_column("Requests",   justify="right",  width=10)
    table.add_column("Bar",     style="bright_blue", ratio=1)

    top = s.top_ips.most_common(n)
    max_count = top[0][1] if top else 1
    for i, (ip, count) in enumerate(top, 1):
        bar = _sparkbar(count, max_count, width=18)
        table.add_row(str(i), ip, f"{count:,}", f"[bright_blue]{bar}[/bright_blue]")
    return table


def _status_table(s: Stats) -> Table:
    table = Table(
        title="[bold]Status Codes[/bold]",
        box=box.SIMPLE_HEAD,
        show_lines=False,
        border_style="yellow",
        header_style="bold yellow",
    )
    table.add_column("Code", justify="center", width=6)
    table.add_column("Count", justify="right", width=8)
    table.add_column("%", justify="right", width=7)
    table.add_column("Bar", ratio=1)

    total = s.total_requests or 1
    for code, count in sorted(s.status_codes.items()):
        cls = f"{code // 100}xx"
        colour = _STATUS_COLOURS.get(cls, "white")
        pct = count / total * 100
        bar = _sparkbar(count, total, width=16)
        table.add_row(
            f"[{colour}]{code}[/{colour}]",
            f"{count:,}",
            f"{pct:.1f}%",
            f"[{colour}]{bar}[/{colour}]",
        )
    return table


def _methods_table(s: Stats) -> Table:
    table = Table(
        title="[bold]HTTP Methods[/bold]",
        box=box.SIMPLE_HEAD,
        show_lines=False,
        border_style="green",
        header_style="bold green",
    )
    table.add_column("Method", width=8)
    table.add_column("Count", justify="right", width=8)
    table.add_column("Bar", ratio=1)

    total = s.total_requests or 1
    for method, count in s.methods.most_common():
        colour = _METHOD_COLOURS.get(method, "white")
        bar = _sparkbar(count, total, width=14)
        table.add_row(
            f"[{colour}]{method}[/{colour}]",
            f"{count:,}",
            f"[{colour}]{bar}[/{colour}]",
        )
    return table


def _hourly_chart(s: Stats) -> Panel:
    """Vertical bar chart of requests per hour."""
    if not s.requests_by_hour:
        return Panel("No data", title="Requests by Hour")

    hours = [f"{h:02d}:00" for h in range(24)]
    counts = [s.requests_by_hour.get(f"{h:02d}:00", 0) for h in range(24)]
    max_count = max(counts) if counts else 1

    chart_height = 8
    lines: list[str] = []

    for row in range(chart_height, 0, -1):
        line = ""
        for count in counts:
            threshold = row / chart_height * max_count
            if count >= threshold:
                line += "[bright_cyan]█[/bright_cyan] "
            else:
                line += "  "
        lines.append(line)

    # X axis
    lines.append("[dim]" + "─ " * 24 + "[/dim]")
    hour_labels = ""
    for h in range(0, 24, 3):
        hour_labels += f"{h:02d}    "
    lines.append(f"[dim]{hour_labels}[/dim]")

    body = Text.from_markup("\n".join(lines))
    return Panel(
        body,
        title=f"[bold]Requests by Hour[/bold]  (peak: [bright_cyan]{max(counts):,}[/bright_cyan] @ [bright_cyan]{hours[counts.index(max(counts))]}[/bright_cyan])",
        border_style="cyan",
        padding=(1, 2),
    )


def _errors_table(s: Stats, n: int = 10) -> Table:
    table = Table(
        title="[bold]Recent Errors[/bold]",
        box=box.SIMPLE_HEAD,
        show_lines=False,
        border_style="red",
        header_style="bold red",
    )
    table.add_column("Time",    style="dim",          width=20)
    table.add_column("Status",  justify="center",     width=7)
    table.add_column("Method",  width=8)
    table.add_column("Path",    ratio=2, overflow="fold")
    table.add_column("IP",      width=16)

    for e in s.recent_errors[:n]:
        cls = f"{e.status // 100}xx"
        colour = _STATUS_COLOURS.get(cls, "white")
        table.add_row(
            e.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            f"[{colour}]{e.status}[/{colour}]",
            e.method,
            e.path,
            e.ip,
        )
    return table


def _footer() -> Text:
    t = Text(justify="center")
    t.append("\n  Generated ", style="dim")
    t.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), style="dim")
    t.append("  ·  Built by ", style="dim")
    t.append("Claude", style="bold magenta")
    t.append("  (claude.ai · Anthropic)\n", style="dim")
    return t


# ── Public API ───────────────────────────────────────────────────────────────

def render_dashboard(s: Stats, top_n: int = 15) -> None:
    """Print the full analysis dashboard to the terminal."""
    console.print(_header_panel())
    console.print()

    # Summary stats
    console.print(_summary_panels(s))
    console.print()

    # Top endpoints + Top IPs side by side
    console.print(Columns([_top_paths_table(s, top_n), _top_ips_table(s, 10)], expand=True))
    console.print()

    # Status codes + Methods side by side
    console.print(Columns([_status_table(s), _methods_table(s)], expand=True))
    console.print()

    # Hourly chart
    console.print(_hourly_chart(s))
    console.print()

    # Errors
    if s.recent_errors:
        console.print(_errors_table(s))
        console.print()

    # Footer
    console.print(Panel(_footer(), border_style="dim"))
