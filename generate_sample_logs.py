#!/usr/bin/env python3
# ============================================================
#  generate_sample_logs.py
#  Generates realistic sample Apache access logs for demo/testing
#  Built by Claude (claude.ai) · Anthropic
# ============================================================

import random
import gzip
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── Sample data pools ────────────────────────────────────────────────────────
HUMAN_IPS = [
    "82.45.12.101", "192.168.1.55", "10.0.0.42", "203.0.113.7",
    "198.51.100.23", "185.220.101.5", "2.56.56.12", "91.108.4.74",
    "77.88.5.88", "45.33.32.156", "162.243.168.50", "159.89.133.235",
    "178.62.52.236", "46.101.127.145", "138.197.138.65",
]
BOT_IPS = [
    "66.249.66.1", "66.249.66.2", "207.46.13.5", "157.55.39.250",
    "40.77.167.188",
]
ALL_IPS = HUMAN_IPS * 8 + BOT_IPS  # humans dominate

PATHS = [
    ("/", 800),
    ("/index.html", 300),
    ("/about", 150),
    ("/contact", 120),
    ("/api/v1/users", 400),
    ("/api/v1/products", 350),
    ("/api/v1/orders", 180),
    ("/static/css/main.css", 600),
    ("/static/js/bundle.js", 550),
    ("/static/img/logo.png", 450),
    ("/favicon.ico", 200),
    ("/robots.txt", 100),
    ("/sitemap.xml", 60),
    ("/login", 250),
    ("/logout", 80),
    ("/dashboard", 180),
    ("/admin", 40),
    ("/api/v1/health", 500),
    ("/404-not-real", 0),  # will be assigned 404
    ("/old-page", 0),       # will be 301
]

METHODS_WEIGHTS = [
    ("GET", 85), ("POST", 10), ("PUT", 3), ("DELETE", 1), ("HEAD", 1),
]

STATUS_WEIGHTS = {
    200: 70, 304: 10, 301: 5, 302: 3, 404: 7, 500: 2, 403: 2, 400: 1,
}

HUMAN_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36',
]
BOT_AGENTS = [
    'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
    'Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)',
    'Mozilla/5.0 (compatible; YandexBot/3.0; +http://yandex.com/bots)',
    'curl/7.88.0',
    'python-requests/2.31.0',
]

REFERERS = [
    "-", "-", "-", "-",  # most requests have no referer
    "https://www.google.com/search?q=logparser",
    "https://twitter.com/",
    "https://github.com/",
    "https://news.ycombinator.com/",
]


def _weighted_choice(pool):
    if isinstance(pool, list) and isinstance(pool[0], tuple):
        items, weights = zip(*pool)
        return random.choices(items, weights=weights, k=1)[0]
    return random.choice(pool)


def _random_status(path: str) -> int:
    if "404-not-real" in path:
        return 404
    if "old-page" in path:
        return 301
    if "admin" in path and random.random() < 0.4:
        return 403
    items = list(STATUS_WEIGHTS.keys())
    weights = list(STATUS_WEIGHTS.values())
    return random.choices(items, weights=weights, k=1)[0]


def _random_bytes(status: int, path: str) -> int:
    if status in (301, 302, 304):
        return 0
    if "static" in path or ".png" in path or ".jpg" in path:
        return random.randint(5_000, 200_000)
    if "api" in path:
        return random.randint(200, 8_000)
    return random.randint(1_000, 25_000)


def generate(n: int = 5_000, days: int = 30, output: Path = None, compress: bool = False) -> Path:
    output = output or Path("sample_logs/access.log")
    output.parent.mkdir(parents=True, exist_ok=True)

    end_time = datetime.now(tz=timezone.utc)
    start_time = end_time - timedelta(days=days)

    # Pre-build path weights
    all_paths = [p for p, w in PATHS if w > 0]
    path_weights = [w for _, w in PATHS if w > 0]

    lines = []
    for _ in range(n):
        ip = random.choice(ALL_IPS)
        is_bot = ip in BOT_IPS
        agent = random.choice(BOT_AGENTS if is_bot else HUMAN_AGENTS)

        path = random.choices(all_paths, weights=path_weights, k=1)[0]
        method = _weighted_choice(METHODS_WEIGHTS)
        status = _random_status(path)
        byte_count = _random_bytes(status, path)
        referer = random.choice(REFERERS)

        # Random timestamp within window, biased toward business hours
        seconds_range = int((end_time - start_time).total_seconds())
        ts = start_time + timedelta(seconds=random.randint(0, seconds_range))

        time_str = ts.strftime("%d/%b/%Y:%H:%M:%S %z")

        line = (
            f'{ip} - - [{time_str}] '
            f'"{method} {path} HTTP/1.1" '
            f'{status} {byte_count} '
            f'"{referer}" "{agent}"'
        )
        lines.append(line)

    # Sort chronologically
    lines.sort(key=lambda l: l.split("[")[1].split("]")[0])

    if compress:
        output = output.with_suffix(".log.gz")
        with gzip.open(output, "wt", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    else:
        with open(output, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")

    return output


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate sample Apache access logs  ·  Built by Claude (claude.ai)"
    )
    parser.add_argument("-n",      type=int,  default=5_000, help="Number of log entries (default: 5000)")
    parser.add_argument("--days",  type=int,  default=30,    help="Time window in days (default: 30)")
    parser.add_argument("--out",   type=str,  default="sample_logs/access.log", help="Output file path")
    parser.add_argument("--gz",    action="store_true",       help="Compress output with gzip")
    args = parser.parse_args()

    out = generate(n=args.n, days=args.days, output=Path(args.out), compress=args.gz)
    print(f"Generated {args.n:,} log entries -> {out}")
