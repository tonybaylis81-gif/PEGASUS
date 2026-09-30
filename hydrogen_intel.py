from __future__ import annotations

import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

FEEDS = [
    ("Google News", "https://news.google.com/rss/search?q=hydrogen+hydrogen+discovery+hydrogen+technology&hl=en-CA&gl=CA&ceid=CA:en"),
    ("Google News Natural H2", "https://news.google.com/rss/search?q=%22natural+hydrogen%22+OR+%22geologic+hydrogen%22&hl=en-CA&gl=CA&ceid=CA:en"),
    ("Google News Electrolysis", "https://news.google.com/rss/search?q=hydrogen+electrolysis+electrolyzer&hl=en-CA&gl=CA&ceid=CA:en"),
    ("Google News Storage", "https://news.google.com/rss/search?q=hydrogen+storage+compression+pipeline&hl=en-CA&gl=CA&ceid=CA:en"),
    ("Google News Fuel Cells", "https://news.google.com/rss/search?q=hydrogen+fuel+cell+advancement&hl=en-CA&gl=CA&ceid=CA:en"),
    ("Google News Saskatchewan", "https://news.google.com/rss/search?q=hydrogen+Saskatchewan+natural+hydrogen&hl=en-CA&gl=CA&ceid=CA:en"),
    ("Google News North Dakota", "https://news.google.com/rss/search?q=hydrogen+%22North+Dakota%22&hl=en-CA&gl=CA&ceid=CA:en"),
]

KEYWORDS = {
    "Natural / Geological Hydrogen": ["natural hydrogen", "geologic hydrogen", "geological hydrogen", "white hydrogen", "subsurface hydrogen", "serpentinization", "radiolysis"],
    "Detection / Measurement": ["hydrogen sensor", "hydrogen detection", "hydrogen monitoring", "soil gas", "gas analyzer"],
    "Electrolysis": ["electrolysis", "electrolyzer", "pem electroly", "alkaline electroly", "aem electroly", "solid oxide"],
    "Storage / Compression": ["hydrogen storage", "hydrogen compression", "compressed hydrogen", "cryogenic hydrogen", "metal hydride"],
    "Materials / Welding": ["hydrogen embrittlement", "hydrogen materials", "hydrogen steel", "hydrogen welding", "hydrogen permeation"],
    "Fuel Cells / Conversion": ["fuel cell", "hydrogen power", "hydrogen generator", "hydrogen engine"],
    "Infrastructure": ["hydrogen pipeline", "hydrogen hub", "hydrogen station", "hydrogen infrastructure"],
    "Safety": ["hydrogen leak", "hydrogen safety", "hydrogen explosion", "hydrogen fire"],
}

PRIORITY_REGIONS = ["saskatchewan", "north dakota", "british columbia", "alberta", "canada", "heartland hydrogen"]

def _clean(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()

def _date(value: str) -> str:
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc).isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()

def _category(text: str) -> str:
    low = text.lower()
    for category, words in KEYWORDS.items():
        if any(w in low for w in words):
            return category
    return "General Hydrogen"

def _relevance(text: str) -> str:
    low = text.lower()
    if any(k in low for k in ["saskatchewan", "north dakota", "british columbia", "alberta", "heartland hydrogen"]):
        return "DIRECTLY RELEVANT"
    if any(any(w in low for w in words) for words in KEYWORDS.values()):
        return "POTENTIALLY RELEVANT"
    return "BACKGROUND"

def fetch_feed(source: str, url: str, timeout: int = 12) -> list[dict]:
    request = urllib.request.Request(url, headers={"User-Agent": "PEGASUS-Valhalla-Hydrogen-Intelligence/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        root = ET.fromstring(response.read())
    items = []
    for node in root.findall(".//item"):
        title = _clean(node.findtext("title", ""))
        link = node.findtext("link", "")
        description = _clean(node.findtext("description", ""))
        pub = node.findtext("pubDate", "")
        if title:
            items.append({
                "source": source,
                "title": title,
                "link": link,
                "published": _date(pub),
                "category": _category(title + " " + description),
                "relevance": _relevance(title + " " + description),
                "summary": description[:500],
            })
    return items

def scan_hydrogen() -> dict:
    articles = []
    errors = []
    seen = set()
    for source, url in FEEDS:
        try:
            for item in fetch_feed(source, url):
                key = (item["title"].lower(), item["link"])
                if key not in seen:
                    seen.add(key)
                    articles.append(item)
        except Exception as exc:
            errors.append(f"{source}: {exc}")
    articles.sort(key=lambda x: x["published"], reverse=True)
    return {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "articles": articles,
        "errors": errors,
        "feed_count": len(FEEDS),
    }

def build_report(scan: dict) -> str:
    articles = scan["articles"]
    lines = [
        "# VALHALLA HYDROGEN REPORT",
        "",
        f"**Scan time (UTC):** {scan['scanned_at']}",
        f"**Sources scanned:** {scan['feed_count']}",
        f"**Items collected:** {len(articles)}",
        "",
        "## Hydrogen Situation",
        "PEGASUS online intelligence scan completed. Items below are source leads and require verification before being treated as established technical fact.",
        "",
    ]
    for category in KEYWORDS:
        selected = [a for a in articles if a["category"] == category]
        if not selected:
            continue
        lines += [f"## {category}", ""]
        for a in selected[:10]:
            lines += [
                f"### {a['title']}",
                f"- **Source:** {a['source']}",
                f"- **Published:** {a['published']}",
                f"- **Valhalla relevance:** {a['relevance']}",
                f"- **Source:** {a['source']}",
                f"- **[OPEN SOURCE]({a['link']})**",
                f"- **Lead:** {a['summary']}",
                "",
            ]
    if scan["errors"]:
        lines += ["## Feed Errors", ""] + [f"- {e}" for e in scan["errors"]]
    return "\n".join(lines)
