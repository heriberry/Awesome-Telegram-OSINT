#!/usr/bin/env python3
"""Simple OSINT search tool using a 50-engine pack."""

import argparse
from engines_50 import search_multiple_engines, SEARCH_ENGINES


def engine_mega50(sess, q, depth):
    """Wrapper around search_multiple_engines.

    Depth is mapped to max_results_per_engine = max(1, min(5, depth//2)).
    Returns list of tuples (source, title, url, snippet).
    """
    per = max(1, min(5, depth // 2))
    engines = [k for k, v in SEARCH_ENGINES.items() if v.get("active", True)]
    rows = []
    try:
        for src_title, title, url, snippet in search_multiple_engines(
            q, engines, max_results_per_engine=per
        ):
            rows.append((src_title, title, url, snippet))
    except Exception:
        pass
    return rows


ENGINES = {
    "mega50": engine_mega50,
}

DEFAULT_ENGINES = ["mega50"]


def search(query, engines=None, depth=4):
    """Search helper that dispatches to registered engines."""
    if engines is None:
        engines = DEFAULT_ENGINES
    rows = []
    for key in engines:
        engine_func = ENGINES.get(key)
        if engine_func:
            rows.extend(engine_func(None, query, depth))
    return rows


def main():
    parser = argparse.ArgumentParser(
        description="OSINT search across multiple engines"
    )
    parser.add_argument("query", help="Search query")
    parser.add_argument(
        "-e",
        "--engines",
        default=",".join(DEFAULT_ENGINES),
        help="Comma separated engines (default: mega50)",
    )
    parser.add_argument(
        "-d", "--depth", type=int, default=4, help="Search depth"
    )
    args = parser.parse_args()
    engines = args.engines.split(",") if args.engines else DEFAULT_ENGINES
    results = search(args.query, engines, args.depth)
    for src, title, url, _ in results:
        print(f"[{src}] {title}\n{url}\n")


if __name__ == "__main__":
    main()
