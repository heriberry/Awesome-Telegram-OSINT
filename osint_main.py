#!/usr/bin/env python3
"""
Enhanced OSINT Main - Improved search coverage and error handling
"""
import os
import re
import sys
import csv
import json
import time
import html
import hashlib
import argparse
from collections import OrderedDict
from datetime import datetime
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode, quote

import requests
from bs4 import BeautifulSoup

DEFAULT_DEPTH = 8
REQUEST_TIMEOUT = 15
MAX_RETRIES = 3
BACKOFF_BASE = 1.6
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXPORT_DIR = os.path.join(BASE_DIR, "exports")
os.makedirs(EXPORT_DIR, exist_ok=True)

# Enhanced User Agents
USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
]

# Working search engines
SEARX_INSTANCES = [
    "https://searx.be",
    "https://searx.tiekoetter.com",
    "https://search.sapti.me",
    "https://searx.prvcy.eu",
]

def get_random_ua():
    import random
    return random.choice(USER_AGENTS)

def normalize_url(u: str) -> str:
    try:
        p = urlparse(u)
        q = OrderedDict(
            (k, v)
            for k, v in parse_qsl(p.query, keep_blank_values=True)
            if not k.lower().startswith(("utm_", "gclid", "fbclid", "yclid", "icid", "mc_"))
        )
        return urlunparse(p._replace(query=urlencode(q, doseq=True)))
    except Exception:
        return u

def hash_key(title: str, url: str) -> str:
    h = hashlib.sha256()
    h.update((title.strip() + "||" + normalize_url(url)).encode("utf-8", "ignore"))
    return h.hexdigest()

def req_get(session, url, *, params=None):
    last = None
    for i in range(MAX_RETRIES):
        try:
            session.headers.update({"User-Agent": get_random_ua()})
            r = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            if r.status_code in (429, 503) and i < MAX_RETRIES - 1:
                time.sleep((BACKOFF_BASE ** i) + 0.5)
                continue
            if r.status_code == 200:
                return r
            if r.status_code in (404, 403):
                return None
            r.raise_for_status()
            return r
        except Exception as e:  # noqa: F841
            last = e
            time.sleep((BACKOFF_BASE ** i) + 0.5)
    print(f"❌ Failed after {MAX_RETRIES} retries: {url}")
    return None

def soup_of(txt):
    return BeautifulSoup(txt, "html.parser")

def file_sanitize(s):
    x = re.sub(r"[^A-Za-z0-9_.-]+", "_", s.strip())[:100]
    return x or "query"

# Enhanced DuckDuckGo search
def engine_ddg(sess, q, depth):
    print("  🦆 Searching DuckDuckGo...")
    base = "https://duckduckgo.com/html/"
    out = []
    for page in range(depth):
        params = {"q": q, "s": str(page * 30), "dc": str(page * 30), "v": "l", "o": "json"}
        r = req_get(sess, base, params=params)
        if not r:
            continue
        s = soup_of(r.text)
        links_found = 0
        for a in s.select("a.result__a"):
            t = a.get_text(" ", strip=True)
            u = a.get("href")
            if u and t:
                out.append(("duckduckgo", t, u))
                links_found += 1
        if links_found == 0:
            break
        time.sleep(1.2)
    return out

# Enhanced Bing search via direct scraping
def engine_bing(sess, q, depth):
    print("  🔍 Searching Bing...")
    base = "https://www.bing.com/search"
    out = []
    for page in range(depth):
        params = {"q": q, "first": str(page * 10 + 1)}
        r = req_get(sess, base, params=params)
        if not r:
            continue
        s = soup_of(r.text)
        links_found = 0
        for a in s.select("h2 a, .b_title a"):
            t = a.get_text(" ", strip=True)
            u = a.get("href")
            if u and u.startswith("http") and t:
                out.append(("bing", t, u))
                links_found += 1
        if links_found == 0:
            break
        time.sleep(1.5)
    return out

# Working SearX implementation
def engine_searx(sess, q, depth):
    print("  🔎 Searching SearXNG instances...")
    out = []
    for instance in SEARX_INSTANCES:
        try:
            for page in range(min(depth, 3)):
                params = {"q": q, "pageno": str(page + 1), "format": "html"}
                r = req_get(sess, f"{instance}/search", params=params)
                if not r:
                    continue
                s = soup_of(r.text)
                links_found = 0
                for result in s.select(".result"):
                    title_elem = result.select_one("h3 a, .result_header")
                    if title_elem:
                        t = title_elem.get_text(" ", strip=True)
                        u = title_elem.get("href")
                        if u and u.startswith("http") and t:
                            out.append(("searxng", t, u))
                            links_found += 1
                if links_found > 0:
                    time.sleep(1.0)
                else:
                    break
            if out:
                break
        except Exception as e:  # noqa: F841
            print(f"    ⚠️ SearX instance {instance} failed: {e}")
            continue
    return out

# Social media specific searches
def engine_social(sess, q, depth):  # noqa: ARG001
    print("  📱 Searching social platforms...")
    out = []
    platforms = [
        ("twitter.com", "site:twitter.com OR site:x.com"),
        ("instagram.com", "site:instagram.com"),
        ("facebook.com", "site:facebook.com"),
        ("linkedin.com", "site:linkedin.com"),
        ("github.com", "site:github.com"),
        ("reddit.com", "site:reddit.com"),
    ]
    base = "https://duckduckgo.com/html/"
    for platform, site_query in platforms[:3]:
        search_query = f"{site_query} {q}"
        params = {"q": search_query, "v": "l", "o": "json"}
        r = req_get(sess, base, params=params)
        if not r:
            continue
        s = soup_of(r.text)
        for a in s.select("a.result__a")[:5]:
            t = a.get_text(" ", strip=True)
            u = a.get("href")
            if u and platform in u:
                out.append((f"social_{platform.split('.')[0]}", t, u))
        time.sleep(1.0)
    return out

# Enhanced email/username specific search
def engine_email_specific(sess, q, depth):  # noqa: ARG001
    if "@" not in q:
        return []
    print("  📧 Email-specific searches...")
    out = []
    email_queries = [
        f'"{q}" breach OR leaked OR "data breach"',
        f'"{q}" found OR discovered',
        f'"{q.split("@")[0]}" {q.split("@")[1]}',
        f'site:haveibeenpwned.com "{q}"',
        f'site:breachdirectory.org "{q}"',
    ]
    base = "https://duckduckgo.com/html/"
    for query in email_queries:
        params = {"q": query, "v": "l", "o": "json"}
        r = req_get(sess, base, params=params)
        if not r:
            continue
        s = soup_of(r.text)
        for a in s.select("a.result__a")[:3]:
            t = a.get_text(" ", strip=True)
            u = a.get("href")
            if u and t:
                out.append(("email_search", t, u))
        time.sleep(1.0)
    return out

# Enhanced wayback machine
def engine_wayback(sess, q, depth):  # noqa: ARG001
    print("  ⏰ Searching Wayback Machine...")
    out = []
    if re.search(r"[A-Za-z0-9-]+\.[A-Za-z]{2,}", q):
        targets = [q, f"www.{q}"]
    else:
        targets = [f"*{q}*"]
    for target in targets:
        try:
            url = f"https://web.archive.org/cdx/search/cdx?url={quote(target)}&output=json&limit=20"
            r = req_get(sess, url)
            if r and r.text:
                data = json.loads(r.text)
                if len(data) > 1:
                    for row in data[1:5]:
                        timestamp, original = row[1], row[2]
                        wayback_url = f"https://web.archive.org/web/{timestamp}/{original}"
                        out.append(("wayback", f"Archived {original} ({timestamp})", wayback_url))
        except Exception:  # noqa: S110
            pass
        time.sleep(0.5)
    return out

# File/document search
def engine_documents(sess, q, depth):  # noqa: ARG001
    print("  📄 Searching for documents...")
    out = []
    file_types = ["pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx"]
    base = "https://duckduckgo.com/html/"
    for ftype in file_types[:3]:
        query = f"{q} filetype:{ftype}"
        params = {"q": query, "v": "l", "o": "json"}
        r = req_get(sess, base, params=params)
        if not r:
            continue
        s = soup_of(r.text)
        for a in s.select("a.result__a")[:2]:
            t = a.get_text(" ", strip=True)
            u = a.get("href")
            if u and t and ftype in u.lower():
                out.append((f"documents_{ftype}", t, u))
        time.sleep(1.0)
    return out

ENGINES = {
    "ddg": engine_ddg,
    "bing": engine_bing,
    "searx": engine_searx,
    "social": engine_social,
    "email": engine_email_specific,
    "wayback": engine_wayback,
    "documents": engine_documents,
}

DEFAULT_ENGINES = ["ddg", "bing", "searx", "social", "wayback", "documents"]

def telegram_notify(txt: str):
    tok = os.getenv("TELEGRAM_BOT_TOKEN")
    chat = os.getenv("TELEGRAM_CHAT_ID")
    if not tok or not chat:
        return False
    try:
        url = f"https://api.telegram.org/bot{tok}/sendMessage"
        data = {
            "chat_id": chat,
            "text": txt[:4000],
            "disable_web_page_preview": True,
            "parse_mode": "HTML",
        }
        r = requests.post(url, json=data, timeout=REQUEST_TIMEOUT)
        return r.ok and r.json().get("ok", False)
    except Exception as e:  # noqa: F841
        print(f"⚠️ Telegram notify failed: {e}")
        return False

def detect_query_type(query: str) -> str:
    if "@" in query and "." in query:
        return "email"
    if re.match(r"^[a-fA-F0-9]{32,}$", query):
        return "hash"
    if re.search(r"[A-Za-z0-9-]+\.[A-Za-z]{2,}", query):
        return "domain"
    if re.match(r"^[a-zA-Z0-9_.-]+$", query):
        return "username"
    return "general"

def run_search(query: str, engines: list, depth: int):
    if depth < DEFAULT_DEPTH:
        depth = DEFAULT_DEPTH
    sess = requests.Session()
    sess.headers.update(
        {
            "User-Agent": get_random_ua(),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
    )
    seen = set()
    rows = []
    query_type = detect_query_type(query)
    print(f"📋 Query type detected: {query_type}")
    print("🔍 Starting search engines...")
    for name in engines:
        engine_func = ENGINES.get(name)
        if not engine_func:
            continue
        try:
            if name == "email" and query_type != "email":
                continue
            results = engine_func(sess, query, depth)
            for src, title, url in results:
                u = normalize_url(url)
                t = html.unescape((title or "").strip())
                if not u or not t or len(t) < 3:
                    continue
                key = hash_key(t, u)
                if key in seen:
                    continue
                seen.add(key)
                rows.append(
                    {
                        "source": src,
                        "title": t[:300],
                        "url": u,
                        "query_type": query_type,
                    }
                )
        except Exception as e:  # noqa: F841
            print(f"    ❌ Engine {name} failed: {e}")
            continue
    return rows

def export_results(query, rows):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"results_{file_sanitize(query)}_{ts}"
    csv_p = os.path.join(EXPORT_DIR, base + ".csv")
    json_p = os.path.join(EXPORT_DIR, base + ".json")
    with open(csv_p, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp_utc", "query", "source", "title", "url", "query_type"])
        for r in rows:
            writer.writerow([ts, query, r["source"], r["title"], r["url"], r.get("query_type", "unknown")])
    with open(json_p, "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp_utc": ts,
                "query": query,
                "query_type": detect_query_type(query),
                "count": len(rows),
                "results": rows,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    return csv_p, json_p

def format_telegram_report(query, rows, query_type):
    report = f"🎯 <b>OSINT Search Complete</b>\n"
    report += f"📋 Target: <code>{query}</code>\n"
    report += f"📊 Type: {query_type}\n"
    report += f"✅ Results: {len(rows)}\n\n"
    if not rows:
        return report + "❌ No results found."
    by_source = {}
    for r in rows:
        source = r["source"]
        by_source.setdefault(source, []).append(r)
    report += "<b>📈 Results by Source:</b>\n"
    for source, results in by_source.items():
        report += f"├ {source}: {len(results)} results\n"
    report += f"\n<b>🔍 Top {min(5, len(rows))} Results:</b>\n"
    for i, r in enumerate(rows[:5], 1):
        title = r["title"][:80] + "..." if len(r["title"]) > 80 else r["title"]
        report += f"{i}. <b>[{r['source']}]</b> {title}\n"
    if len(rows) > 5:
        report += f"\n💡 <i>+{len(rows) - 5} more results in CSV/JSON files</i>"
    return report

def main():
    parser = argparse.ArgumentParser(description="Enhanced OSINT searcher with improved coverage")
    parser.add_argument("query", help="Search term, email, username, domain, or hash")
    parser.add_argument(
        "-d",
        "--depth",
        type=int,
        default=DEFAULT_DEPTH,
        help=f"Pages per engine (default: {DEFAULT_DEPTH})",
    )
    parser.add_argument(
        "--engines",
        default=",".join(DEFAULT_ENGINES),
        help="Comma list. Available: " + ", ".join(ENGINES.keys()),
    )
    parser.add_argument("--no-telegram", action="store_true", help="Disable Telegram notifications")
    parser.add_argument("--telegram-only", action="store_true", help="Send only summary to Telegram")
    args = parser.parse_args()
    query = args.query.strip()
    engines = [e.strip() for e in args.engines.split(",") if e.strip()]
    print("🚀 Enhanced OSINT Intelligence Search")
    print("=" * 50)
    print(f"🎯 Target: {query}")
    print(f"🧰 Engines: {', '.join(engines)}")
    print(f"🔎 Depth per engine: {args.depth}")
    print()
    start_time = time.time()
    rows = run_search(query, engines, args.depth)
    search_time = time.time() - start_time
    rows = sorted(rows, key=lambda r: (r["source"], r["title"].lower()))
    csv_path, json_path = export_results(query, rows)
    print(f"\n✅ Search completed in {search_time:.2f}s")
    print(f"📊 Total results: {len(rows)}")
    print(f"📄 CSV: {csv_path}")
    print(f"📄 JSON: {json_path}")
    if not args.no_telegram:
        query_type = detect_query_type(query)
        telegram_msg = format_telegram_report(query, rows, query_type)
        print(f"\n📤 Sending Telegram notification...")
        if telegram_notify(telegram_msg):
            print("✅ Telegram notification sent!")
        else:
            print("❌ Failed to send Telegram notification")
    if rows:
        print(f"\n🔍 Sample Results ({min(10, len(rows))} of {len(rows)}):")
        print("-" * 60)
        for i, r in enumerate(rows[:10], 1):
            title = r["title"][:70] + "..." if len(r["title"]) > 70 else r["title"]
            print(f"{i:2d}. [{r['source']}] {title}")
    else:
        print("\n❌ No results found. Try:")
        print("   - Different search terms")
        print("   - Checking your internet connection")
        print("   - Using fewer engines if rate limited")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print('Usage: python osint_main.py "<query>" [-d DEPTH] [--engines ...]')
        print('Example: python osint_main.py "john.doe@example.com" -d 10')
        sys.exit(1)
    main()

