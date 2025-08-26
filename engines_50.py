#!/usr/bin/env python3
import re, csv, json, time, random, hashlib
from datetime import datetime
from urllib.parse import urlparse, quote
import requests
from bs4 import BeautifulSoup

SEARCH_ENGINES = {
    "google":{"name":"Google","url":"https://www.google.com/search","params":{"q":"{query}"},"selectors":["h3 a",".g a h3",".LC20lb"],"active":True},
    "bing":{"name":"Microsoft Bing","url":"https://www.bing.com/search","params":{"q":"{query}"},"selectors":["h2 a",".b_title a",".b_algo a"],"active":True},
    "yahoo":{"name":"Yahoo Search","url":"https://search.yahoo.com/search","params":{"p":"{query}"},"selectors":["h3 a",".title a",".compTitle a"],"active":True},
    "duckduckgo":{"name":"DuckDuckGo","url":"https://duckduckgo.com/html/","params":{"q":"{query}"},"selectors":["a.result__a","h2 a"],"active":True},
    "baidu":{"name":"Baidu","url":"https://www.baidu.com/s","params":{"wd":"{query}"},"selectors":["h3 a",".t a"],"active":True},
    "startpage":{"name":"Startpage","url":"https://www.startpage.com/sp/search","params":{"query":"{query}"},"selectors":["h3 a",".w-gl__result-title"],"active":True},
    "searx":{"name":"SearXNG","url":"https://searx.be/search","params":{"q":"{query}"},"selectors":[".result h3 a",".result_header"],"active":True},
    "qwant":{"name":"Qwant","url":"https://www.qwant.com/","params":{"q":"{query}","t":"web"},"selectors":["h3 a",".external"],"active":True},
    "swisscows":{"name":"Swisscows","url":"https://swisscows.com/web","params":{"query":"{query}"},"selectors":[".web-result h3 a",".title"],"active":True},
    "brave":{"name":"Brave Search","url":"https://search.brave.com/search","params":{"q":"{query}"},"selectors":[".title a","h3 a"],"active":True},
    "yandex":{"name":"Yandex","url":"https://yandex.com/search/","params":{"text":"{query}"},"selectors":["h2 a",".organic__title-wrapper a"],"active":True},
    "ecosia":{"name":"Ecosia","url":"https://www.ecosia.org/search","params":{"q":"{query}"},"selectors":[".result__title a","h2 a"],"active":True},
    "dogpile":{"name":"Dogpile","url":"https://www.dogpile.com/serp","params":{"q":"{query}"},"selectors":[".web-source__title a","h3 a"],"active":True},
    "metacrawler":{"name":"MetaCrawler","url":"https://www.metacrawler.com/serp","params":{"q":"{query}"},"selectors":[".web-source__title a",".title a"],"active":True},
    "excite":{"name":"Excite","url":"https://www.excite.com/search/web","params":{"q":"{query}"},"selectors":[".result-title a","h3 a"],"active":True},
    "wolfram":{"name":"Wolfram Alpha","url":"https://www.wolframalpha.com/input/","params":{"i":"{query}"},"selectors":[".pod-title",".plaintext"],"active":True},
    "scholar":{"name":"Google Scholar","url":"https://scholar.google.com/scholar","params":{"q":"{query}"},"selectors":["h3 a",".gs_rt a"],"active":True},
    "semantic":{"name":"Semantic Scholar","url":"https://www.semanticscholar.org/search","params":{"q":"{query}"},"selectors":[".cl-paper-title a","h3 a"],"active":True},
    "base":{"name":"BASE Academic","url":"https://www.base-search.net/Search/Results","params":{"lookfor":"{query}"},"selectors":[".title a","h3 a"],"active":True},
    "core":{"name":"CORE","url":"https://core.ac.uk/search","params":{"q":"{query}"},"selectors":[".title a","h3 a"],"active":True},
    "naver":{"name":"Naver","url":"https://search.naver.com/search.naver","params":{"query":"{query}"},"selectors":[".title_link","h3 a"],"active":True},
    "seznam":{"name":"Seznam","url":"https://search.seznam.cz/","params":{"q":"{query}"},"selectors":[".Result-title a","h3 a"],"active":True},
    "sogou":{"name":"Sogou","url":"https://www.sogou.com/web","params":{"query":"{query}"},"selectors":[".pt a","h3 a"],"active":True},
    "so360":{"name":"360 Search","url":"https://www.so.com/s","params":{"q":"{query}"},"selectors":[".res-title a","h3 a"],"active":True},
    "youtube":{"name":"YouTube","url":"https://www.youtube.com/results","params":{"search_query":"{query}"},"selectors":["#video-title",".ytd-video-meta-block"],"active":True},
    "reddit":{"name":"Reddit","url":"https://www.reddit.com/search/","params":{"q":"{query}"},"selectors":[".search-result-link","._eYtD2XCVieq6emjKBH3m"],"active":True},
    "twitter":{"name":"Twitter/X","url":"https://twitter.com/search","params":{"q":"{query}"},"selectors":["[data-testid='tweet']",".tweet"],"active":True},
    "instagram":{"name":"Instagram","url":"https://www.instagram.com/explore/tags/{query}/","params":{},"selectors":["article a","._aagw"],"active":False},
    "linkedin":{"name":"LinkedIn","url":"https://www.linkedin.com/search/results/all/","params":{"keywords":"{query}"},"selectors":[".result-title",".entity-result__title"],"active":False},
    "amazon":{"name":"Amazon","url":"https://www.amazon.com/s","params":{"k":"{query}"},"selectors":["[data-component-type='s-search-result'] h2 a",".s-link-style"],"active":True},
    "ebay":{"name":"eBay","url":"https://www.ebay.com/sch/i.html","params":{"_nkw":"{query}"},"selectors":[".s-item__title",".it-ttl a"],"active":True},
    "etsy":{"name":"Etsy","url":"https://www.etsy.com/search","params":{"q":"{query}"},"selectors":[".listing-link",".v2-listing-card__title"],"active":True},
    "hotbot":{"name":"HotBot","url":"https://www.hotbot.com/search","params":{"q":"{query}"},"selectors":[".web-source__title a","h3 a"],"active":True},
    "lycos":{"name":"Lycos","url":"https://search.lycos.com/web/","params":{"q":"{query}"},"selectors":[".result-title a","h3 a"],"active":True},
    "aol":{"name":"AOL Search","url":"https://search.aol.com/aol/search","params":{"q":"{query}"},"selectors":[".algo-title a","h3 a"],"active":True},
    "ask":{"name":"Ask.com","url":"https://www.ask.com/web","params":{"q":"{query}"},"selectors":[".PartialSearchResults-item-title a",".web-result h3 a"],"active":True},
    "shodan":{"name":"Shodan","url":"https://www.shodan.io/search","params":{"query":"{query}"},"selectors":[".search-result",".title"],"active":True},
    "censys":{"name":"Censys","url":"https://search.censys.io/search","params":{"q":"{query}"},"selectors":[".result-item",".title"],"active":True},
    "pipl":{"name":"Pipl","url":"https://pipl.com/search/","params":{"q":"{query}"},"selectors":[".person-result",".name"],"active":False},
    "scribd":{"name":"Scribd","url":"https://www.scribd.com/search","params":{"query":"{query}"},"selectors":[".title_link",".document_link"],"active":True},
    "slideshare":{"name":"SlideShare","url":"https://www.slideshare.net/search/slideshow","params":{"q":"{query}"},"selectors":[".slideshow-title a",".title"],"active":True},
    "issuu":{"name":"Issuu","url":"https://issuu.com/search","params":{"q":"{query}"},"selectors":[".title a",".publication-title"],"active":True},
    "wayback":{"name":"Wayback Machine","url":"https://web.archive.org/web/*/","params":{},"selectors":["a",".results a"],"active":True},
    "archive":{"name":"Archive.org","url":"https://archive.org/search.php","params":{"query":"{query}"},"selectors":[".item-title a",".titleLink"],"active":True},
    "gibiru":{"name":"Gibiru","url":"https://gibiru.com/results.html","params":{"q":"{query}"},"selectors":[".web_results h3 a",".title a"],"active":True},
    "mojeek":{"name":"Mojeek","url":"https://www.mojeek.com/search","params":{"q":"{query}"},"selectors":[".title a",".url-title a"],"active":True},
    "disconnect":{"name":"Disconnect Search","url":"https://search.disconnect.me/searchTerms/search","params":{"query":"{query}"},"selectors":[".result h3 a",".title"],"active":True},
    "gigablast":{"name":"Gigablast","url":"https://www.gigablast.com/search","params":{"q":"{query}"},"selectors":[".title a",".result .url"],"active":True},
    "onesearch":{"name":"OneSearch","url":"https://www.onesearch.com/yhs/search","params":{"p":"{query}"},"selectors":[".title a",".compTitle a"],"active":True},
    "searchencrypt":{"name":"Search Encrypt","url":"https://www.searchencrypt.com/search","params":{"q":"{query}"},"selectors":[".web-result h3 a",".title"],"active":True}
}

USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0"
]

def _ua():
    import random
    return random.choice(USER_AGENTS)

def _sess():
    s = requests.Session()
    s.headers.update({
        "User-Agent": _ua(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    })
    return s

def _search_one(engine_key, query, max_results=5, sleep_min=0.6, sleep_max=1.4):
    eng = SEARCH_ENGINES.get(engine_key)
    if not eng or not eng.get("active"): return []
    session = _sess()
    params = {}
    for k,v in eng.get("params",{}).items():
        params[k] = v.format(query=quote(query))
    url = eng["url"]
    try:
        r = session.get(url, params=params, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        out=[]
        seen=set()
        for sel in eng["selectors"]:
            els = soup.select(sel)
            for el in els[:max_results]:
                if el.name == "a":
                    title = el.get_text(strip=True)
                    href  = el.get("href") or ""
                else:
                    title = el.get_text(strip=True)
                    a = el.find("a", href=True)
                    href = a.get("href") if a else ""
                if not href: continue
                if href.startswith("/"):
                    href = f"https://{urlparse(url).netloc}{href}"
                if not href.startswith("http"): continue
                h = hashlib.md5(href.encode()).hexdigest()
                if h in seen: continue
                seen.add(h)
                if title:
                    out.append((f"mega50:{eng['name']}", title[:300], href, ""))
            if out: break
        time.sleep(random.uniform(sleep_min, sleep_max))
        return out[:max_results]
    except Exception:
        return []

def search_multiple_engines(query, engines=None, max_results_per_engine=3, active_only=True):
    if engines is None:
        engines = [k for k,v in SEARCH_ENGINES.items() if (v.get("active", True) or not active_only)]
    rows=[]
    for key in engines:
        rows.extend(_search_one(key, query, max_results=max_results_per_engine))
    return rows
