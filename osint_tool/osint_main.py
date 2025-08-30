#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
osint_main.py — Multi-engine OSINT mit strukturierten Outputs
Outputs pro Lauf:
- CSV:      timestamp_utc, query, source, title, url, snippet, page_title, meta_description, text_excerpt
- JSON:     strukturierte Liste
- JSONL:    1 Result/Zeile (NDJSON)
- SQLite:   exports/osint_results.sqlite (Tabelle results + Indizes)
- HTML:     Offline-Report mit Suche/Sortierung (keine externen CDNs)
Kompatibel mit bestehenden Engines inkl. "mega50" (falls integriert).
"""

import os, re, sys, csv, json, time, html, argparse, hashlib, sqlite3
from collections import OrderedDict
from datetime import datetime, timezone
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode, quote, urljoin

import requests
from bs4 import BeautifulSoup

# ---- Konfig ----
DEFAULT_DEPTH = 6
REQUEST_TIMEOUT = 15
MAX_RETRIES = 3
BACKOFF_BASE = 1.6
ENRICH_TOP_N = 60    # Anzahl Einträge für content fetch
EXCERPT_LEN = 800
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXPORT_DIR = os.path.join(BASE_DIR, "exports")
CUSTOM_FILE = os.path.join(BASE_DIR, "custom_sites.txt")
os.makedirs(EXPORT_DIR, exist_ok=True)

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")

def load_dotenv():
    p = os.path.join(BASE_DIR, ".env")
    if not os.path.isfile(p): return
    for line in open(p, "r", encoding="utf-8"):
        line=line.strip()
        if not line or line.startswith("#") or "=" not in line: continue
        k,v = line.split("=",1)
        if k and v and k not in os.environ:
            os.environ[k]=v

def normalize_url(u: str) -> str:
    try:
        p = urlparse(u)
        q = OrderedDict((k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
                        if not k.lower().startswith(("utm_", "gclid", "fbclid", "yclid", "icid", "mc_")))
        return urlunparse(p._replace(query=urlencode(q, doseq=True)))
    except Exception:
        return u

def hash_key(title: str, url: str) -> str:
    h = hashlib.sha256()
    h.update((title.strip()+"||"+normalize_url(url)).encode("utf-8","ignore"))
    return h.hexdigest()

def req_get(session, url, *, params=None):
    last = None
    for i in range(MAX_RETRIES):
        try:
            r = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            if r.status_code in (429,503) and i < MAX_RETRIES-1:
                time.sleep((BACKOFF_BASE**i)+0.5); continue
            r.raise_for_status()
            return r
        except Exception as e:
            last = e; time.sleep((BACKOFF_BASE**i)+0.5)
    raise last

def soup_of(txt): return BeautifulSoup(txt, "lxml")
def paged(depth): return range(depth)

def file_sanitize(s: str) -> str:
    s = s.strip().splitlines()[0]
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'[^A-Za-z0-9_. -]+', '_', s)[:120]
    s = s.strip().replace(' ', '_')
    return s or "query"

def clean_query(q: str) -> str:
    q = q.strip().splitlines()[0]
    return q

def first_text(soup: BeautifulSoup, maxlen=EXCERPT_LEN) -> str:
    for tag in soup(["script","style","noscript","header","footer","svg","nav","form","img","source"]): 
        tag.decompose()
    txt = ' '.join(t.strip() for t in soup.get_text(separator=' ').split())
    return txt[:maxlen]

# ---- Engines (Basis; weitere via mega50-Wrapper) ----
def engine_ddg(sess,q,depth):
    base="https://duckduckgo.com/html/"
    out=[]
    for page in paged(depth):
        p={"q":q,"s":str(page*30),"dc":str(page*30),"v":"l","o":"json"}
        s=soup_of(req_get(sess,base,params=p).text)
        for res in s.select("div.result"):
            a = res.select_one("a.result__a")
            if not a: continue
            t=a.get_text(" ",strip=True); u=a.get("href")
            sn = res.select_one(".result__snippet")
            snippet = sn.get_text(" ", strip=True) if sn else ""
            if u: out.append(("duckduckgo", t, u, snippet))
        time.sleep(0.5)
    return out

def engine_ddg_lite(sess,q,depth):
    base="https://lite.duckduckgo.com/lite/"
    out=[]
    for page in paged(depth):
        s=soup_of(req_get(sess,base,params={"q":q,"s":str(page*30)}).text)
        for li in s.select("td > a"):
            href=li.get("href") or ""
            if href.startswith("http"):
                t=li.get_text(" ",strip=True)
                if t: out.append(("duckduckgo_lite", t, href, ""))
        time.sleep(0.4)
    return out

def engine_mojeek(sess,q,depth):
    base="https://www.mojeek.com/search"
    out=[]
    for page in paged(depth):
        s=soup_of(req_get(sess,base,params={"q":q,"s":str(page*10)}).text)
        for b in s.select("div.result"):
            a=b.select_one("a.result-title, h2 a")
            if not a: continue
            t=a.get_text(" ",strip=True); u=a.get("href")
            sn=b.select_one(".result-extract")
            snippet=sn.get_text(" ",strip=True) if sn else ""
            if u and u.startswith("http"): out.append(("mojeek",t,u,snippet))
        time.sleep(0.4)
    return out

def engine_metager(sess,q,depth):
    base="https://metager.org/meta/meta.ger3"
    out=[]
    for page in paged(depth):
        s=soup_of(req_get(sess,base,params={"eingabe":q,"page":str(page+1)}).text)
        for r in s.select("div.result, .result-container"):
            a=r.select_one("a.result-link, h2 a")
            if not a: continue
            u=a.get("href"); t=a.get_text(" ",strip=True)
            sn=r.get_text(" ", strip=True)
            if u and u.startswith("http"): out.append(("metager", t, u, sn[:220]))
        time.sleep(0.4)
    return out

def engine_github(sess,q,depth):
    base="https://github.com/search"
    out=[]
    for page in paged(depth):
        s=soup_of(req_get(sess,base,params={"q":q,"type":"code","p":str(page+1)}).text)
        for a in s.select("a.v-align-middle, a.Link--primary"):
            t=a.get_text(" ",strip=True); u="https://github.com"+(a.get("href") or "")
            if u.startswith("https://github.com"): out.append(("github", t, u, ""))
        time.sleep(0.4)
    return out

def engine_wayback(sess,q,depth):
    out=[]
    looks_domain = re.search(r"[A-Za-z0-9-]+\.[A-Za-z]{2,}", q) is not None
    targets=[q] if looks_domain else [f"*{q}*"]
    for t in targets:
        for _ in paged(depth):
            s=soup_of(req_get(sess,"https://web.archive.org/web/*/"+quote(t)).text)
            for a in s.select("a"):
                href=a.get("href") or ""
                if href.startswith("http") and "web.archive.org" in href:
                    out.append(("wayback", a.get_text(" ",strip=True) or "Wayback snapshot", href, ""))
            time.sleep(0.3)
    return out

def engine_crtsh(sess,q,depth):
    if not re.search(r"[A-Za-z0-9-]+\.[A-Za-z]{2,}", q): return []
    out=[]; base="https://crt.sh/"
    for page in paged(depth):
        s=soup_of(req_get(sess,base,params={"q":q,"dir":"y","page":str(page+1)}).text)
        for a in s.select("a[href^='?id=']"):
            u=base + a.get("href"); t=a.get_text(" ",strip=True) or "crt.sh entry"
            out.append(("crtsh", t, u, ""))
        time.sleep(0.3)
    return out

def engine_stackoverflow(sess,q,depth):
    base="https://stackoverflow.com/search"
    out=[]
    for page in paged(depth):
        s=soup_of(req_get(sess,base,params={"q":q,"page":str(page+1),"tab":"Relevance"}).text)
        for row in s.select("div.question-summary, div.s-post-summary"):
            a=row.select_one("a.question-hyperlink")
            if not a: continue
            t=a.get_text(" ",strip=True); h=a.get("href") or ""
            if h.startswith("/questions/"):
                u="https://stackoverflow.com"+h
                sn=row.get_text(" ",strip=True)
                out.append(("stackoverflow", t, u, sn[:220]))
        time.sleep(0.4)
    return out

def engine_reddit(sess,q,depth):
    base="https://old.reddit.com/search"
    out=[]; after=None
    for _ in paged(depth):
        p={"q":q,"sort":"relevance","t":"all"}
        if after: p["after"]=after
        s=soup_of(req_get(sess,base,params=p).text)
        for item in s.select("div.search-result"):
            a=item.select_one("a.search-title")
            if not a: continue
            t=a.get_text(" ",strip=True); u=a.get("href")
            sn=item.select_one(".search-expando")
            snippet=sn.get_text(" ",strip=True) if sn else ""
            if u: out.append(("reddit", t, u, snippet[:220]))
        nxt=s.select_one("span.next-button > a"); after=None
        if nxt:
            from urllib.parse import parse_qsl
            qs=dict(parse_qsl(urlparse(nxt.get("href")).query)); after=qs.get("after")
        time.sleep(0.4)
    return out
# Optionaler mega50-Wrapper (falls engines_50.py installiert)
def engine_mega50(sess, q, depth):
    try:
        from engines_50 import search_multiple_engines, SEARCH_ENGINES
    except Exception:
        return []
    per = max(1, min(5, depth//2))
    engines = [k for k,v in SEARCH_ENGINES.items() if v.get("active", True)]
    rows=[]
    try:
        for (src_title, title, url, snippet) in search_multiple_engines(q, engines, max_results_per_engine=per):
            rows.append((src_title, title, url, snippet))
    except Exception:
        pass
    return rows

ENGINES = {
    "mega50": engine_mega50,   # bleibt still, wenn engines_50 fehlt
    "ddg": engine_ddg,
    "ddg_lite": engine_ddg_lite,
    "mojeek": engine_mojeek,
    "metager": engine_metager,
    "stackoverflow": engine_stackoverflow,
    "github": engine_github,
    "wayback": engine_wayback,
    "crtsh": engine_crtsh,
    "reddit": engine_reddit,
}

DEFAULT_ENGINES = ["mega50","ddg","ddg_lite","mojeek","metager","reddit","stackoverflow","github","wayback","crtsh"]

def enrich_fetch(sess, url: str):
    try:
        r = req_get(sess, url)
        s = soup_of(r.text)
        title = (s.title.get_text(" ", strip=True) if s.title else "")[:300]
        meta = s.select_one("meta[name='description'], meta[property='og:description']")
        mdesc = (meta.get("content") or "").strip()[:700] if meta else ""
        excerpt = first_text(s, EXCERPT_LEN)
        return title, mdesc, excerpt
    except Exception:
        return "", "", ""

def telegram_notify(text: str):
    tok=os.getenv("TELEGRAM_BOT_TOKEN"); chat=os.getenv("TELEGRAM_CHAT_ID")
    if not tok or not chat: return
    try:
        requests.post(f"https://api.telegram.org/bot{tok}/sendMessage",
                      json={"chat_id":chat,"text":text[:4000],"disable_web_page_preview":True},
                      timeout=REQUEST_TIMEOUT).raise_for_status()
    except Exception:
        pass

def run_search(query: str, engines: list, depth: int):
    if depth < DEFAULT_DEPTH: depth = DEFAULT_DEPTH
    sess=requests.Session()
    sess.headers.update({"User-Agent":UA,"Accept-Language":"en;q=0.9"})
    rows=[]; seen=set()
    for name in engines:
        fn=ENGINES.get(name)
        if not fn: continue
        try:
            for src, title, url, snippet in fn(sess, query, depth):
                u=normalize_url(url); t=html.unescape((title or "").strip())
                if not u or not t: continue
                key=hash_key(t,u)
                if key in seen: continue
                seen.add(key)
                rows.append({
                    "id": key,
                    "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "query": query,
                    "source": src,
                    "title": t[:300],
                    "url": u,
                    "snippet": snippet
                })
        except Exception:
            continue
    # Enrichment
    for i, r in enumerate(rows[:ENRICH_TOP_N]):
        pt, md, ex = enrich_fetch(sess, r["url"])
        r["page_title"]=pt; r["meta_description"]=md; r["text_excerpt"]=ex
    for r in rows[ENRICH_TOP_N:]:
        r["page_title"]=""; r["meta_description"]=""; r["text_excerpt"]=""
    return rows

# ---- Exporte ----
def export_all(query: str, rows: list):
    ts=datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe=file_sanitize(query)
    base=f"{safe}_{ts}"
    csv_p=os.path.join(EXPORT_DIR, f"results_{base}.csv")
    json_p=os.path.join(EXPORT_DIR, f"results_{base}.json")
    jsonl_p=os.path.join(EXPORT_DIR, f"results_{base}.jsonl")
    md_p=os.path.join(EXPORT_DIR, f"info_{base}.md")
    html_p=os.path.join(EXPORT_DIR, f"report_{base}.html")
    db_p=os.path.join(EXPORT_DIR, "osint_results.sqlite")

    # CSV
    with open(csv_p,"w",newline="",encoding="utf-8") as f:
        w=csv.writer(f)
        w.writerow(["timestamp_utc","query","source","title","url","snippet","page_title","meta_description","text_excerpt","id"])
        for r in rows:
            w.writerow([r.get("timestamp_utc",""), r["query"], r["source"], r["title"], r["url"],
                        r.get("snippet",""), r.get("page_title",""), r.get("meta_description",""), r.get("text_excerpt",""), r["id"]])

    # JSON
    with open(json_p,"w",encoding="utf-8") as f:
        json.dump({"timestamp_utc":ts,"query":query,"count":len(rows),"results":rows}, f, ensure_ascii=False, indent=2)

    # JSONL
    with open(jsonl_p,"w",encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # SQLite
    con = sqlite3.connect(db_p)
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS results (
        id TEXT PRIMARY KEY,
        timestamp_utc TEXT,
        query TEXT,
        source TEXT,
        title TEXT,
        url TEXT,
        snippet TEXT,
        page_title TEXT,
        meta_description TEXT,
        text_excerpt TEXT
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_results_query ON results(query)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_results_source ON results(source)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_results_url ON results(url)")
    cur.executemany("""
        INSERT OR IGNORE INTO results
        (id, timestamp_utc, query, source, title, url, snippet, page_title, meta_description, text_excerpt)
        VALUES (:id, :timestamp_utc, :query, :source, :title, :url, :snippet, :page_title, :meta_description, :text_excerpt)
    """, rows)
    con.commit(); con.close()

    # Markdown
    with open(md_p,"w",encoding="utf-8") as f:
        f.write(f"# OSINT Results — {query}\n\n")
        f.write(f"- Time (UTC): {ts}\n- Count: {len(rows)}\n\n")
        for i,r in enumerate(rows,1):
            f.write(f"## {i}. {r['title']}\n")
            f.write(f"- Source: `{r['source']}`\n- URL: {r['url']}\n")
            if r.get('snippet'): f.write(f"- Snippet: {r['snippet']}\n")
            if r.get('page_title'): f.write(f"- Page Title: {r['page_title']}\n")
            if r.get('meta_description'): f.write(f"- Meta: {r['meta_description']}\n")
            if r.get('text_excerpt'): f.write(f"\n> {r['text_excerpt']}\n")
            f.write("\n")

    # HTML (offline, kleines JS für Suche/Sort)
    def esc(x): 
        if x is None: return ""
        return (str(x).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;"))
    rows_html = "".join(
        f"<tr>"
        f"<td>{esc(r.get('timestamp_utc',''))}</td>"
        f"<td>{esc(r['source'])}</td>"
        f"<td>{esc(r['title'])}</td>"
        f"<td><a href='{esc(r['url'])}' target='_blank' rel='noreferrer'>{esc(r['url'])}</a></td>"
        f"<td>{esc(r.get('snippet',''))}</td>"
        f"<td>{esc(r.get('page_title',''))}</td>"
        f"<td>{esc(r.get('meta_description',''))}</td>"
        f"<td>{esc(r.get('text_excerpt',''))}</td>"
        f"</tr>"
        for r in rows
    )
    html_doc = f"""<!doctype html>
<html lang="de"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>OSINT Report — {esc(query)}</title>
<style>
body{{font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Arial; margin:20px}}
h1{{font-size:20px; margin:0 0 12px}}
.small{{color:#555}}
input[type=search]{{padding:8px; width:100%; max-width:420px; border:1px solid #bbb; border-radius:8px;}}
table{{border-collapse:collapse; width:100%; margin-top:12px;}}
th,td{{border:1px solid #e2e8f0; padding:8px; vertical-align:top;}}
th{{background:#f8fafc; cursor:pointer; position:sticky; top:0;}}
tr:nth-child(even){{background:#fafafa}}
td a{{text-decoration:none;}}
.count{{margin-top:6px; font-size:12px; color:#444}}
</style>
</head><body>
<h1>OSINT Report — {esc(query)}</h1>
<div class="small">Time (UTC): {ts} • Results: {len(rows)}</div>
<input id="filter" type="search" placeholder="Suche in allen Spalten…">
<div class="count" id="count"></div>
<table id="tbl">
<thead><tr>
<th data-k="timestamp">Zeit</th>
<th data-k="source">Quelle</th>
<th data-k="title">Titel</th>
<th data-k="url">URL</th>
<th data-k="snippet">Snippet</th>
<th data-k="pagetitle">Page Title</th>
<th data-k="meta">Meta Description</th>
<th data-k="text">Textauszug</th>
</tr></thead>
<tbody>
{rows_html}
</tbody>
</table>
<script>
const tbl=document.getElementById('tbl');
const filter=document.getElementById('filter');
const cnt=document.getElementById('count');
function updateCount(){{cnt.textContent=tbl.tBodies[0].querySelectorAll('tr:not([hidden])').length+' sichtbar';}}
filter.addEventListener('input',()=>{{const q=filter.value.toLowerCase();for(const tr of tbl.tBodies[0].rows){{tr.hidden=!tr.textContent.toLowerCase().includes(q);}}updateCount();}});
let sortCol=0, asc=true;
for(const [i,th] of [...tbl.tHead.rows[0].cells].entries()){{
  th.addEventListener('click',()=>{{
    const rows=[...tbl.tBodies[0].rows];
    asc = sortCol===i ? !asc : true; sortCol=i;
    rows.sort((a,b)=>a.cells[i].textContent.localeCompare(b.cells[i].textContent, 'de', {{numeric:true}}*(i===0)));
    if(!asc) rows.reverse(); for(const r of rows) tbl.tBodies[0].appendChild(r);
  }})
}}
updateCount();
</script>
</body></html>"""
    with open(html_p,"w",encoding="utf-8") as f: f.write(html_doc)

    return csv_p, json_p, jsonl_p, db_p, md_p, html_p

def main():
    load_dotenv()
    ap=argparse.ArgumentParser(description="OSINT Multi-Engine mit strukturierten Outputs")
    ap.add_argument("query", help="Suchbegriff / E-Mail / Username / Domain / Hash")
    ap.add_argument("-d","--depth", type=int, default=DEFAULT_DEPTH, help="Seiten pro Engine (min 6)")
    ap.add_argument("--engines", default=",".join(DEFAULT_ENGINES), help="Liste, z.B. mega50,ddg,mojeek")
    ap.add_argument("--no-telegram", action="store_true", help="Telegram aus")
    args=ap.parse_args()

    query=clean_query(args.query)
    engines=[e.strip() for e in args.engines.split(",") if e.strip()]

    print("🚀 OSINT Intelligence Search")
    print("="*40)
    print(f"🎯 Target: {query}")
    print(f"🧰 Engines: {', '.join(engines)}")
    print(f"🔎 Depth per engine: {max(DEFAULT_DEPTH,args.depth)}\n")

    rows=run_search(query, engines, args.depth)
    rows=sorted(rows, key=lambda r:(r["source"], r["title"].lower()))

    csv_p, json_p, jsonl_p, db_p, md_p, html_p = export_all(query, rows)

    print(f"✅ Results: {len(rows)}")
    print(f"📄 CSV:   {csv_p}")
    print(f"🧾 JSON:  {json_p}")
    print(f"📚 JSONL: {jsonl_p}")
    print(f"🗄️ DB:    {db_p}  (table: results)")
    print(f"📘 INFO:  {md_p}")
    print(f"🖥️ HTML:  {html_p}")

    if not args.no_telegram:
        telegram_notify(f"OSINT search '{query}' complete. Results: {len(rows)}")

if __name__=="__main__":
    if len(sys.argv)==1:
        print('Usage: python osint_main.py "<query>" [-d DEPTH] [--engines ...]')
        sys.exit(1)
    main()
