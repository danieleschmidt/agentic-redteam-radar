"""
CLI entry point for agentic-redteam-radar.

Usage:
    python -m redteam_radar.cli --url http://localhost:11434 --style ollama --model llama3
    python -m redteam_radar.cli --url https://api.openai.com --style openai --model gpt-4 --api-key sk-...
    python -m redteam_radar.cli --url http://myapp/chat --style raw --categories prompt_injection jailbreak
"""

import argparse
import logging
import sys
import os

from .endpoint import Endpoint
from .scanner import Scanner
from .reporter import to_json, to_text
from .probes import CATEGORIES


def main():
    parser = argparse.ArgumentParser(
        prog="redteam-radar",
        description="Automated adversarial scanner for LLM/agent endpoints.",
    )
    parser.add_argument("--url", required=True, help="Target endpoint base URL")
    parser.add_argument(
        "--style",
        default="openai",
        choices=["openai", "ollama", "raw"],
        help="Endpoint API style (default: openai)",
    )
    parser.add_argument("--model", default="gpt-3.5-turbo", help="Model name to use")
    parser.add_argument("--api-key", default=None, help="API key (or set OPENAI_API_KEY env var)")
    parser.add_argument(
        "--system-prompt",
        default=None,
        help="Optional system prompt to send with each probe",
    )
    parser.add_argument(
        "--categories",
        nargs="+",
        choices=list(CATEGORIES.keys()),
        default=None,
        help="Limit scan to specific categories (default: all)",
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=200,
        help="Milliseconds between probes (default: 200)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Write JSON report to this file (default: stdout text report only)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON report to stdout instead of text",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="HTTP timeout per probe in seconds (default: 30)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose probe-by-probe logging")

    args = parser.parse_args()

    # Logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s  %(levelname)s  %(message)s")

    api_key = args.api_key or os.environ.get("OPENAI_API_KEY")

    endpoint = Endpoint(
        url=args.url,
        style=args.style,
        model=args.model,
        api_key=api_key,
        system_prompt=args.system_prompt,
        timeout=args.timeout,
    )

    scanner = Scanner(
        endpoint=endpoint,
        categories=args.categories,
        delay_ms=args.delay,
        verbose=args.verbose,
    )

    report = scanner.run()

    if args.json:
        print(to_json(report))
    else:
        print(to_text(report))

    if args.output:
        with open(args.output, "w") as f:
            f.write(to_json(report))
        print(f"\nJSON report written to {args.output}")

    # Exit 1 if vulnerabilities found (useful for CI)
    sys.exit(1 if report.vulnerable else 0)


if __name__ == "__main__":
    main()
