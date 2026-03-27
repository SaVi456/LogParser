# LogParser

> **Built by [Claude](https://claude.ai) (Anthropic)**
> An intelligent Apache / Nginx access log analyser with a rich terminal dashboard.

---

## What it does

LogParser parses Apache and Nginx access logs and renders an interactive terminal dashboard showing:

- **Summary stats** — total requests, unique IPs, bandwidth transferred, error rate, req/sec
- **Top endpoints** — most-hit paths with bandwidth and visual bar charts
- **Top IPs** — highest-traffic client addresses
- **Status code breakdown** — per-code counts and percentages with colour coding
- **HTTP method distribution** — GET / POST / PUT / DELETE breakdown
- **Hourly traffic chart** — ASCII bar chart of requests across the 24-hour clock
- **Recent errors** — last 20 4xx / 5xx entries with timestamp, path, and IP

Supports plain `.log` files and gzip-compressed `.log.gz` files. Can also read from stdin.

---

## Built with Claude

This project was designed and written entirely by **Claude** (claude.ai), Anthropic's AI assistant.
Every module — from the regex parser to the Rich dashboard — was authored through a conversation.

---

## Installation

```bash
git clone https://github.com/your-username/LogParser.git
cd LogParser
pip install -r requirements.txt
```

**Requirements:** Python 3.10+, `rich`, `click`

---

## Quick start

```bash
# Generate sample logs for demo
python generate_sample_logs.py

# Run the dashboard
python main.py sample_logs/access.log
```

---

## Usage

```
python main.py LOGFILE [OPTIONS]

Arguments:
  LOGFILE   Path to the log file, or '-' to read from stdin

Options:
  -n, --top INTEGER     Number of top entries per table  [default: 15]
  -s, --status INTEGER  Filter to a specific HTTP status code
  -m, --method TEXT     Filter to a specific HTTP method (GET, POST …)
      --ip TEXT         Filter to requests from a specific IP address
      --no-bots         Exclude detected bot / crawler traffic
      --export-json FILE  Export summary stats to JSON
  -v, --version         Show version and exit
  -h, --help            Show this message and exit
```

### Examples

```bash
# Analyse a log file
python main.py /var/log/nginx/access.log

# Show only 404 errors
python main.py access.log --status 404

# Exclude bots, show top 20 endpoints
python main.py access.log --no-bots --top 20

# Filter to a single IP address
python main.py access.log --ip 82.45.12.101

# Read from stdin (pipe)
cat access.log | python main.py -

# Read a gzip-compressed log
python main.py access.log.gz

# Export stats to JSON for further processing
python main.py access.log --export-json stats.json
```

---

## Sample log generator

```bash
# 5 000 entries, last 30 days (default)
python generate_sample_logs.py

# 50 000 entries, last 90 days, gzip compressed
python generate_sample_logs.py -n 50000 --days 90 --gz
```

---

## Project structure

```
LogParser/
├── log_parser/
│   ├── __init__.py      # Package metadata
│   ├── parser.py        # Regex parser — LogEntry dataclass
│   ├── analyzer.py      # Stats aggregation — Stats dataclass
│   └── dashboard.py     # Rich terminal dashboard renderer
├── main.py              # CLI entry point (click)
├── generate_sample_logs.py  # Demo log generator
├── requirements.txt
└── README.md
```

---

## Log format

LogParser handles the **Apache Combined Log Format** (also the default Nginx format):

```
%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\"
```

Example:
```
82.45.12.101 - - [27/Mar/2026:14:23:01 +0000] "GET /api/v1/users HTTP/1.1" 200 3412 "https://google.com" "Mozilla/5.0 …"
```

---

## License

MIT — free to use, modify, and distribute.

---

*Built by [Claude](https://claude.ai) · Anthropic*
