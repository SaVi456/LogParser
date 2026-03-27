#!/usr/bin/env python3
# ============================================================
#  main.py — thin shim for running the CLI directly
#  Built by Claude (claude.ai) · Anthropic
#
#  Usage:
#    python main.py <logfile> [options]
#
#  When installed via pip, use the `logparser` command instead.
# ============================================================

from log_parser.cli import cli

if __name__ == "__main__":
    cli()
