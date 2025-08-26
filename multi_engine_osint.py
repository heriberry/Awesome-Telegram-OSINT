#!/usr/bin/env python3
"""
50 Free Search Engines for OSINT Integration
Complete list with URL templates and integration methods
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
import random
from collections import OrderedDict
from datetime import datetime
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode, quote

import requests
from bs4 import BeautifulSoup

# 50 Free Search Engines Configuration
SEARCH_ENGINES = {
    # Major Search Engines
    "google": {
        "name": "Google",
        "url": "https://www.google.com/search",
        "params": {"q": "{query}"},
        "selectors": ["h3 a", ".g a h3", ".LC20lb"],
        "active": True,
    },
    "bing": {
        "name": "Microsoft Bing",
        "url": "https://www.bing.com/search",
        "params": {"q": "{query}"},
        "selectors": ["h2 a", ".b_title a", ".b_algo a"],
        "active": True,
    },
    "yahoo": {
        "name": "Yahoo Search",
        "url": "https://search.yahoo.com/search",
        "params": {"p": "{query}"},
        "selectors": ["h3 a", ".title a", ".compTitle a"],
        "active": True,
    },
    "duckduckgo": {
        "name": "DuckDuckGo",
        "url": "https://duckduckgo.com/html/",
        "params": {"q": "{query}"},
        "selectors": ["a.result__a", "h2 a"],
        "active": True,
    },
    "baidu": {
        "name": "Baidu",
        "url": "https://www.baidu.com/s",
        "params": {"wd": "{query}"},
        "selectors": ["h3 a", ".t a"],
        "active": True,
    },
    # Privacy-Focused Engines
    "startpage": {
        "name": "Startpage",
        "url": "https://www.startpage.com/sp/search",
        "params": {"query": "{query}"},
        "selectors": ["h3 a", ".w-gl__result-title"],
        "active": True,
    },
    "searx": {
        "name": "SearXNG",
        "url": "https://searx.be/search",
        "params": {"q": "{query}"},
        "selectors": [".result h3 a", ".result_header"],
        "active": True,
    },
    "qwant": {
        "name": "Qwant",
        "url": "https://www.qwant.com/",
        "params": {"q": "{query}", "t": "web"},
        "selectors": ["h3 a", ".external"],
        "active": True,
    },
    "swisscows": {
        "name": "Swisscows",
        "url": "https://swisscows.com/web",
        "params": {"query": "{query}"},
        "selectors": [".web-result h3 a", ".title"],
        "active": True,
    },
    "brave": {
        "name": "Brave Search",
        "url": "https://search.brave.com/search",
        "params": {"q": "{query}"},
        "selectors": [".title a", "h3 a"],
        "active": True,
    },
    # Alternative Engines
    "yandex": {
        "name": "Yandex",
        "url": "https://yandex.com/search/",
        "params": {"text": "{query}"},
        "selectors": ["h2 a", ".organic__title-wrapper a"],
        "active": True,
    },
    "ecosia": {
        "name": "Ecosia",
        "url": "https://www.ecosia.org/search",
        "params": {"q": "{query}"},
        "selectors": [".result__title a", "h2 a"],
        "active": True,
    },
    "dogpile": {
        "name": "Dogpile",
        "url": "https://www.dogpile.com/serp",
        "params": {"q": "{query}"},
        "selectors": [".web-source__title a", "h3 a"],
        "active": True,
    },
    "metacrawler": {
        "name": "MetaCrawler",
        "url": "https://www.metacrawler.com/serp",
        "params": {"q": "{query}"},
        "selectors": [".web-source__title a", ".title a"],
        "active": True,
    },
    "excite": {
        "name": "Excite",
        "url": "https://www.excite.com/search/web",
        "params": {"q": "{query}"},
        "selectors": [".result-title a", "h3 a"],
        "active": True,
    },
    # Specialized/Academic
    "wolfram": {
        "name": "Wolfram Alpha",
        "url": "https://www.wolframalpha.com/input/",
        "params": {"i": "{query}"},
        "selectors": [".pod-title", ".plaintext"],
        "active": True,
    },
    "scholar": {
        "name": "Google Scholar",
        "url": "https://scholar.google.com/scholar",
        "params": {"q": "{query}"},
        "selectors": ["h3 a", ".gs_rt a"],
        "active": True,
    },
    "semantic": {
        "name": "Semantic Scholar",
        "url": "https://www.semanticscholar.org/search",
        "params": {"q": "{query}"},
        "selectors": [".cl-paper-title a", "h3 a"],
        "active": True,
    },
    "base": {
        "name": "BASE Academic",
        "url": "https://www.base-search.net/Search/Results",
        "params": {"lookfor": "{query}"},
        "selectors": [".title a", "h3 a"],
        "active": True,
    },
    "core": {
        "name": "CORE",
        "url": "https://core.ac.uk/search",
        "params": {"q": "{query}"},
        "selectors": [".title a", "h3 a"],
        "active": True,
    },
    # Regional/Language Specific
    "naver": {
        "name": "Naver",
        "url": "https://search.naver.com/search.naver",
        "params": {"query": "{query}"},
        "selectors": [".title_link", "h3 a"],
        "active": True,
    },
    "seznam": {
        "name": "Seznam",
        "url": "https://search.seznam.cz/",
        "params": {"q": "{query}"},
        "selectors": [".Result-title a", "h3 a"],
        "active": True,
    },
    "sogou": {
        "name": "Sogou",
        "url": "https://www.sogou.com/web",
        "params": {"query": "{query}"},
        "selectors": [".pt a", "h3 a"],
        "active": True,
    },
    "so360": {
        "name": "360 Search",
        "url": "https://www.so.com/s",
        "params": {"q": "{query}"},
        "selectors": [".res-title a", "h3 a"],
        "active": True,
    },
    # Social/Media Search
    "youtube": {
        "name": "YouTube",
        "url": "https://www.youtube.com/results",
        "params": {"search_query": "{query}"},
        "selectors": ["#video-title", ".ytd-video-meta-block"],
        "active": True,
    },
    "reddit": {
        "name": "Reddit",
        "url": "https://www.reddit.com/search/",
        "params": {"q": "{query}"},
        "selectors": [".search-result-link", "._eYtD2XCVieq6emjKBH3m"],
        "active": True,
    },
    "twitter": {
        "name": "Twitter/X",
        "url": "https://twitter.com/search",
        "params": {"q": "{query}"},
        "selectors": ["[data-testid='tweet']", ".tweet"],
        "active": True,
    },
    "instagram": {
        "name": "Instagram",
        "url": "https://www.instagram.com/explore/tags/{query}/",
        "params": {},
        "selectors": ["article a", "._aagw"],
        "active": False,
    },
    "linkedin": {
        "name": "LinkedIn",
        "url": "https://www.linkedin.com/search/results/all/",
        "params": {"keywords": "{query}"},
        "selectors": [".result-title", ".entity-result__title"],
        "active": False,
    },
    # Shopping/E-commerce
    "amazon": {
        "name": "Amazon",
        "url": "https://www.amazon.com/s",
        "params": {"k": "{query}"},
        "selectors": ["[data-component-type='s-search-result'] h2 a", ".s-link-style"],
        "active": True,
    },
    "ebay": {
        "name": "eBay",
        "url": "https://www.ebay.com/sch/i.html",
        "params": {"_nkw": "{query}"},
        "selectors": [".s-item__title", ".it-ttl a"],
        "active": True,
    },
    "etsy": {
        "name": "Etsy",
        "url": "https://www.etsy.com/search",
        "params": {"q": "{query}"},
        "selectors": [".listing-link", ".v2-listing-card__title"],
        "active": True,
    },
    # News/Information
    "hotbot": {
        "name": "HotBot",
        "url": "https://www.hotbot.com/search",
        "params": {"q": "{query}"},
        "selectors": [".web-source__title a", "h3 a"],
        "active": True,
    },
    "lycos": {
        "name": "Lycos",
        "url": "https://search.lycos.com/web/",
        "params": {"q": "{query}"},
        "selectors": [".result-title a", "h3 a"],
        "active": True,
    },
    "aol": {
        "name": "AOL Search",
        "url": "https://search.aol.com/aol/search",
        "params": {"q": "{query}"},
        "selectors": [".algo-title a", "h3 a"],
        "active": True,
    },
    "ask": {
        "name": "Ask.com",
        "url": "https://www.ask.com/web",
        "params": {"q": "{query}"},
        "selectors": [".PartialSearchResults-item-title a", ".web-result h3 a"],
        "active": True,
    },
    # Specialty/Technical
    "shodan": {
        "name": "Shodan",
        "url": "https://www.shodan.io/search",
        "params": {"query": "{query}"},
        "selectors": [".search-result", ".title"],
        "active": True,
    },
    "censys": {
        "name": "Censys",
        "url": "https://search.censys.io/search",
        "params": {"q": "{query}"},
        "selectors": [".result-item", ".title"],
        "active": True,
    },
    "scribd": {
        "name": "Scribd",
        "url": "https://www.scribd.com/search",
        "params": {"query": "{query}"},
        "selectors": [".title_link", ".document_link"],
        "active": True,
    },
    "slideshare": {
        "name": "SlideShare",
        "url": "https://www.slideshare.net/search/slideshow",
        "params": {"q": "{query}"},
        "selectors": [".slideshow-title a", ".title"],
        "active": True,
    },
    "issuu": {
        "name": "Issuu",
        "url": "https://issuu.com/search",
        "params": {"q": "{query}"},
        "selectors": [".title a", ".publication-title"],
        "active": True,
    },
    # Archive/Historical
    "wayback": {
        "name": "Wayback Machine",
        "url": "https://web.archive.org/web/*/",
        "params": {},
        "selectors": ["a", ".results a"],
        "active": True,
    },
    "archive": {
        "name": "Archive.org",
        "url": "https://archive.org/search.php",
        "params": {"query": "{query}"},
        "selectors": [".item-title a", ".titleLink"],
        "active": True,
    },
    # Privacy/Anonymous
    "gibiru": {
        "name": "Gibiru",
        "url": "https://gibiru.com/results.html",
        "params": {"q": "{query}"},
        "selectors": [".web_results h3 a", ".title a"],
        "active": True,
    },
    "mojeek": {
        "name": "Mojeek",
        "url": "https://www.mojeek.com/search",
        "params": {"q": "{query}"},
        "selectors": [".title a", ".url-title a"],
        "active": True,
    },
    "disconnect": {
        "name": "Disconnect Search",
        "url": "https://search.disconnect.me/searchTerms/search",
        "params": {"query": "{query}"},
        "selectors": [".result h3 a", ".title"],
        "active": True,
    },
    # Additional Engines
    "gigablast": {
        "name": "Gigablast",
        "url": "https://www.gigablast.com/search",
        "params": {"q": "{query}"},
        "selectors": [".title a", ".result .url"],
        "active": True,
    },
    "onesearch": {
        "name": "OneSearch",
        "url": "https://www.onesearch.com/yhs/search",
        "params": {"p": "{query}"},
        "selectors": [".title a", ".compTitle a"],
        "active": True,
    },
    "searchencrypt": {
        "name": "Search Encrypt",
        "url": "https://www.searchencrypt.com/search",
        "params": {"q": "{query}"},
        "selectors": [".web-result h3 a", ".title"],
        "active": True,
    },
}

# User agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
]

class MultiEngineOSINT:
    def __init__(self):
        self.session = requests.Session()
        self.results = []
        self.seen_urls = set()

    def get_random_ua(self):
        return random.choice(USER_AGENTS)

    def search_engine(self, engine_key, query, max_results=10):
        engine = SEARCH_ENGINES.get(engine_key)
        if not engine or not engine.get("active"):
            return []
        results = []
        try:
            url = engine["url"]
            params = {}
            for key, value in engine["params"].items():
                params[key] = value.format(query=quote(query))
            self.session.headers.update(
                {
                    "User-Agent": self.get_random_ua(),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate",
                    "Connection": "keep-alive",
                    "Referer": f"https://{urlparse(url).netloc}/",
                }
            )
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            for selector in engine["selectors"]:
                elements = soup.select(selector)
                for elem in elements[:max_results]:
                    title = (
                        elem.get_text(strip=True)
                        if elem.name != "a"
                        else elem.get_text(strip=True)
                    )
                    href = elem.get("href") if elem.name == "a" else elem.find("a", href=True)
                    if href and isinstance(href, str):
                        url_result = href
                    elif href and hasattr(href, "get"):
                        url_result = href.get("href", "")
                    else:
                        continue
                    if url_result.startswith("/"):
                        url_result = f"https://{urlparse(engine['url']).netloc}{url_result}"
                    elif not url_result.startswith("http"):
                        continue
                    url_hash = hashlib.md5(url_result.encode()).hexdigest()
                    if url_hash in self.seen_urls:
                        continue
                    self.seen_urls.add(url_hash)
                    if title and url_result:
                        results.append(
                            {
                                "engine": engine["name"],
                                "title": title[:200],
                                "url": url_result,
                                "query": query,
                            }
                        )
                if results:
                    break
            time.sleep(random.uniform(1, 2))
        except Exception as e:  # noqa: F841
            print(f"    ❌ {engine['name']}: {str(e)[:50]}...")
        return results[:max_results]

    def search_multiple_engines(self, query, engines=None, max_results_per_engine=5):
        if engines is None:
            engines = [k for k, v in SEARCH_ENGINES.items() if v.get("active", True)]
        all_results = []
        print(f"🔍 Searching {len(engines)} engines for: {query}")
        print("=" * 60)
        for engine_key in engines:
            engine_name = SEARCH_ENGINES.get(engine_key, {}).get("name", engine_key)
            print(f"  🔎 {engine_name}...", end=" ")
            results = self.search_engine(engine_key, query, max_results_per_engine)
            if results:
                print(f"✅ {len(results)} results")
                all_results.extend(results)
            else:
                print("❌ No results")
        return all_results

    def export_results(self, results, query):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_query = re.sub(r"[^a-zA-Z0-9_.-]", "_", query)[:50]
        csv_file = f"multi_engine_results_{safe_query}_{timestamp}.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["timestamp", "query", "engine", "title", "url"])
            writer.writeheader()
            for result in results:
                writer.writerow(
                    {
                        "timestamp": timestamp,
                        "query": query,
                        "engine": result["engine"],
                        "title": result["title"],
                        "url": result["url"],
                    }
                )
        json_file = f"multi_engine_results_{safe_query}_{timestamp}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "timestamp": timestamp,
                    "query": query,
                    "total_results": len(results),
                    "engines_used": list({r['engine'] for r in results}),
                    "results": results,
                },
                f,
                indent=2,
                ensure_ascii=False,
            )
        return csv_file, json_file

def list_all_engines():
    print("🔍 Available Search Engines (50 Total)")
    print("=" * 60)
    categories = {
        "Major": ["google", "bing", "yahoo", "duckduckgo", "baidu"],
        "Privacy": ["startpage", "searx", "qwant", "swisscows", "brave"],
        "Alternative": ["yandex", "ecosia", "dogpile", "metacrawler", "excite"],
        "Academic": ["wolfram", "scholar", "semantic", "base", "core"],
        "Regional": ["naver", "seznam", "sogou", "so360"],
        "Social": ["youtube", "reddit", "twitter", "instagram", "linkedin"],
        "Shopping": ["amazon", "ebay", "etsy"],
        "News": ["hotbot", "lycos", "aol", "ask"],
        "Technical": ["shodan", "censys"],
        "Documents": ["scribd", "slideshare", "issuu"],
        "Archive": ["wayback", "archive"],
        "Anonymous": ["gibiru", "mojeek", "disconnect"],
        "Other": ["gigablast", "onesearch", "searchencrypt"],
    }
    for category, engines in categories.items():
        print(f"\n📂 {category} Engines:")
        for engine_key in engines:
            engine = SEARCH_ENGINES.get(engine_key, {})
            status = "✅" if engine.get("active", False) else "❌"
            name = engine.get("name", engine_key)
            print(f"   {status} {name} ({engine_key})")

def main():
    parser = argparse.ArgumentParser(
        description="Multi-Engine OSINT Search with 50 Search Engines"
    )
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument("--engines", help="Comma-separated list of engines to use")
    parser.add_argument("--list", action="store_true", help="List all available engines")
    parser.add_argument("--max-per-engine", type=int, default=5, help="Max results per engine")
    parser.add_argument("--active-only", action="store_true", help="Use only active engines")
    args = parser.parse_args()
    if args.list:
        list_all_engines()
        return
    if not args.query:
        print("Usage: python multi_engine_osint.py <query> [options]")
        print("       python multi_engine_osint.py --list")
        return
    osint = MultiEngineOSINT()
    if args.engines:
        selected_engines = [e.strip() for e in args.engines.split(",")]
    else:
        if args.active_only:
            selected_engines = [k for k, v in SEARCH_ENGINES.items() if v.get("active", True)]
        else:
            selected_engines = [
                "google",
                "bing",
                "duckduckgo",
                "startpage",
                "brave",
                "yandex",
                "ecosia",
                "qwant",
                "mojeek",
                "searx",
                "youtube",
                "reddit",
                "scholar",
                "wayback",
                "amazon",
                "hotbot",
                "ask",
                "gigablast",
                "lycos",
                "dogpile",
            ]
    results = osint.search_multiple_engines(
        args.query, selected_engines, args.max_per_engine
    )
    if results:
        csv_file, json_file = osint.export_results(results, args.query)
        print(f"\n📊 Search Complete!")
        print(f"   Total Results: {len(results)}")
        print(f"   Engines Used: {len({r['engine'] for r in results})}")
        print(f"   CSV Export: {csv_file}")
        print(f"   JSON Export: {json_file}")
        print(f"\n🎯 Sample Results:")
        for i, result in enumerate(results[:10], 1):
            title = (
                result["title"][:80] + "..." if len(result["title"]) > 80 else result["title"]
            )
            print(f"   {i:2d}. [{result['engine']}] {title}")
        if len(results) > 10:
            print(f"   ... and {len(results) - 10} more results")
    else:
        print("\n❌ No results found across any search engines.")
        print("Try:")
        print("  - Different search terms")
        print("  - Using --engines to specify specific engines")
        print("  - Check your internet connection")

if __name__ == "__main__":
    main()

