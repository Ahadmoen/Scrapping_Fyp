from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote_plus
import json
import re
import xml.etree.ElementTree as ET

import pandas as pd
import requests
from bs4 import BeautifulSoup

from .symbols import SYMBOLS, COMPANIES, GLOBAL_KEYWORDS, GENERAL_QUERIES

GOOGLE_NEWS_BASE = "https://news.google.com/rss/search"
HL, GL, CEID = "en-PK", "PK", "PK:en"
USER_AGENT = "Mozilla/5.0 (compatible; Scrapping_Fyp/1.0)"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "news"


def build_symbol_query(symbol: str) -> str:
    info = COMPANIES.get(symbol, {})
    terms = [info.get("name", symbol), symbol, *info.get("aliases", [])]
    unique = []
    for t in terms:
        if t and t not in unique:
            unique.append(t)
    return " OR ".join(f'"{t}"' if " " in t else t for t in unique)


def fetch_feed(query: str) -> ET.Element:
    url = f"{GOOGLE_NEWS_BASE}?q={quote_plus(query)}&hl={HL}&gl={GL}&ceid={CEID}"
    response = requests.get(url, timeout=30, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    return ET.fromstring(response.content)


def clean_html(html: str) -> str:
    return BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True)


def split_sentences(text: str) -> list:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def match_keywords(text: str, keywords: list) -> tuple:
    lower = text.lower()
    hits = sorted({kw for kw in keywords if kw.lower() in lower})
    sentences = split_sentences(text)
    context = [s for s in sentences if any(kw.lower() in s.lower() for kw in hits)]
    return hits, context


def parse_pubdate(raw: str) -> str:
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except Exception:
        return raw


def parse_items(root: ET.Element) -> list:
    items = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = parse_pubdate(item.findtext("pubDate") or "")
        desc = clean_html(item.findtext("description") or "")
        source_el = item.find("source")
        platform = (source_el.text or "").strip() if source_el is not None else ""
        if platform and title.endswith(f" - {platform}"):
            title = title[: -(len(platform) + 3)]
        items.append({"title": title, "link": link, "pub": pub, "desc": desc, "platform": platform})
    return items


def merge_by_link(path: Path, new_rows: list) -> list:
    combined = new_rows[:]
    if path.exists():
        prev = json.loads(path.read_text())
        combined = prev + combined
    seen = {}
    for row in combined:
        key = row.get("Link") or row.get("Heading")
        if key:
            seen[key] = row
    return sorted(seen.values(), key=lambda r: r.get("Date", ""), reverse=True)


def write_json(path: Path, rows: list) -> None:
    pd.DataFrame(rows).to_json(path, orient="records", indent=2, force_ascii=False)


def scrape_symbol(symbol: str) -> None:
    info = COMPANIES.get(symbol, {})
    industry = info.get("industry", "")
    pool = sorted(set(GLOBAL_KEYWORDS + [symbol] + info.get("aliases", []) + info.get("keywords", [])))
    query = build_symbol_query(symbol)

    try:
        root = fetch_feed(query)
    except Exception as exc:
        print(f"{symbol}: fetch failed: {exc}")
        return

    rows = []
    for item in parse_items(root):
        text = f"{item['title']}. {item['desc']}"
        hits, context = match_keywords(text, pool)
        rows.append({
            "Symbol": symbol,
            "Date": item["pub"],
            "Heading": item["title"],
            "Link": item["link"],
            "Keywords": hits,
            "KeywordContext": context,
            "Market": industry,
            "Platform": item["platform"],
            "Sentiment": None,
        })

    if not rows:
        print(f"{symbol}: 0 items")
        return

    out = OUTPUT_DIR / f"{symbol.lower()}_news.json"
    merged = merge_by_link(out, rows)
    write_json(out, merged)
    print(f"{symbol}: fetched {len(rows)}, total {len(merged)} -> {out}")


def scrape_general() -> None:
    out = OUTPUT_DIR / "general_news.json"
    rows = []
    for query, market in GENERAL_QUERIES:
        try:
            root = fetch_feed(query)
        except Exception as exc:
            print(f"GENERAL [{query}]: fetch failed: {exc}")
            continue
        for item in parse_items(root):
            text = f"{item['title']}. {item['desc']}"
            hits, context = match_keywords(text, GLOBAL_KEYWORDS)
            rows.append({
                "Symbol": "GENERAL",
                "Date": item["pub"],
                "Heading": item["title"],
                "Link": item["link"],
                "Keywords": hits,
                "KeywordContext": context,
                "Market": market,
                "Platform": item["platform"],
                "Sentiment": None,
            })

    if not rows:
        print("GENERAL: no items")
        return

    merged = merge_by_link(out, rows)
    write_json(out, merged)
    print(f"GENERAL: fetched {len(rows)}, total {len(merged)} -> {out}")


def main():
    for symbol in SYMBOLS:
        scrape_symbol(symbol)
    scrape_general()


if __name__ == "__main__":
    main()
