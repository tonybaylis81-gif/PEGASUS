from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

REPO = os.environ["GITHUB_REPOSITORY"]
TOKEN = os.environ["GITHUB_TOKEN"]
API = "https://api.github.com"
REPORT_DIR = Path("hydrogen_reports")
STATE_FILE = Path("hydrogen_seen.json")
ALERT_FILE = Path("HYDROGEN_ALERT.md")

FEEDS = [
    ("Google News - Hydrogen", "https://news.google.com/rss/search?q=hydrogen+discovery+OR+hydrogen+breakthrough+OR+hydrogen+advancement&hl=en-CA&gl=CA&ceid=CA:en"),
    ("Google News - Natural Hydrogen", "https://news.google.com/rss/search?q=%22natural+hydrogen%22+OR+%22geologic+hydrogen%22&hl=en-CA&gl=CA&ceid=CA:en"),
    ("Google News - Electrolysis", "https://news.google.com/rss/search?q=hydrogen+electrolysis+OR+electrolyzer&hl=en-CA&gl=CA&ceid=CA:en"),
    ("Google News - Storage", "https://news.google.com/rss/search?q=hydrogen+storage+OR+hydrogen+compression+OR+hydrogen+pipeline&hl=en-CA&gl=CA&ceid=CA:en"),
    ("Google News - Fuel Cells", "https://news.google.com/rss/search?q=hydrogen+fuel+cell+OR+hydrogen+power&hl=en-CA&gl=CA&ceid=CA:en"),
    ("Google News - Materials", "https://news.google.com/rss/search?q=hydrogen+embrittlement+OR+hydrogen+materials+OR+hydrogen+welding&hl=en-CA&gl=CA&ceid=CA:en"),
    ("Google News - Safety", "https://news.google.com/rss/search?q=hydrogen+leak+detection+OR+hydrogen+safety&hl=en-CA&gl=CA&ceid=CA:en"),
    ("Google News - Saskatchewan", "https://news.google.com/rss/search?q=hydrogen+Saskatchewan+OR+%22natural+hydrogen%22+Saskatchewan&hl=en-CA&gl=CA&ceid=CA:en"),
    ("Google News - North Dakota", "https://news.google.com/rss/search?q=hydrogen+%22North+Dakota%22&hl=en-CA&gl=CA&ceid=CA:en"),
    ("Crossref - Natural Hydrogen", "https://api.crossref.org/works?query.bibliographic=%22natural%20hydrogen%22&filter=from-pub-date:2026-01-01&rows=20&select=DOI,title,published,URL"),
    ("Crossref - Hydrogen Electrolysis", "https://api.crossref.org/works?query.bibliographic=hydrogen%20electrolysis&filter=from-pub-date:2026-01-01&rows=20&select=DOI,title,published,URL"),
]

KEYWORDS = {
    "Natural / Geological Hydrogen": ["natural hydrogen", "geologic hydrogen", "geological hydrogen", "white hydrogen", "subsurface hydrogen", "serpentinization", "radiolysis"],
    "Detection / Measurement": ["hydrogen sensor", "hydrogen detection", "hydrogen monitoring", "soil gas", "gas analyzer"],
    "Electrolysis": ["electrolysis", "electrolyzer", "pem electroly", "alkaline electroly", "aem electroly", "solid oxide"],
    "Storage / Compression": ["hydrogen storage", "hydrogen compression", "compressed hydrogen", "cryogenic hydrogen", "metal hydride"],
    "Materials / Welding": ["hydrogen embrittlement", "hydrogen materials", "hydrogen steel", "hydrogen welding", "hydrogen permeation"],
    "Fuel Cells / Conversion": ["fuel cell", "hydrogen power", "hydrogen generator", "hydrogen engine"],
    "Infrastructure": ["hydrogen pipeline", "hydrogen hub", "hydrogen station", "hydrogen infrastructure"],
    "Safety": ["hydrogen leak", "hydrogen safety", "hydrogen fire"],
}

PRIORITY = ["saskatchewan", "north dakota", "british columbia", "alberta", "heartland hydrogen"]

def clean(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()

def iso_date(s):
    try:
        return parsedate_to_datetime(s).astimezone(timezone.utc).isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()

def category(text):
    low = text.lower()
    for c, words in KEYWORDS.items():
        if any(w in low for w in words):
            return c
    return "General Hydrogen"

def relevance(text):
    low = text.lower()
    if any(k in low for k in PRIORITY):
        return "DIRECTLY RELEVANT"
    if any(w in low for words in KEYWORDS.values() for w in words):
        return "POTENTIALLY RELEVANT"
    return "BACKGROUND"

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "PEGASUS-Valhalla-Hydrogen-Watch/2.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()

def rss(source, url):
    root = ET.fromstring(get(url))
    out = []
    for n in root.findall(".//item"):
        title = clean(n.findtext("title", ""))
        link = n.findtext("link", "")
        desc = clean(n.findtext("description", ""))
        pub = n.findtext("pubDate", "")
        if title:
            out.append({"source": source, "title": title, "link": link, "published": iso_date(pub), "summary": desc[:600]})
    return out

def crossref(source, url):
    data = json.loads(get(url).decode("utf-8"))
    out = []
    for x in data.get("message", {}).get("items", []):
        title = " ".join(x.get("title") or []).strip()
        if not title:
            continue
        pub = x.get("published", {}).get("date-parts", [[2026, 1, 1]])[0]
        dt = "-".join(str(v).zfill(2) for v in (pub + [1, 1])[:3])
        doi = x.get("DOI", "")
        link = x.get("URL") or (f"https://doi.org/{doi}" if doi else "")
        out.append({"source": source, "title": title, "link": link, "published": dt, "summary": "Crossref scholarly publication record."})
    return out

def scan():
    items, errors = [], []
    for source, url in FEEDS:
        try:
            items.extend(crossref(source, url) if source.startswith("Crossref") else rss(source, url))
        except Exception as e:
            errors.append(f"{source}: {e}")
    seen, unique = set(), []
    for x in items:
        key = hashlib.sha256((x["title"].lower() + "|" + x["link"]).encode()).hexdigest()
        if key not in seen:
            seen.add(key)
            x["id"] = key
            text = x["title"] + " " + x["summary"]
            x["category"] = category(text)
            x["relevance"] = relevance(text)
            unique.append(x)
    unique.sort(key=lambda x: x["published"], reverse=True)
    return unique, errors

def api(method, path, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(API + path, data=data, method=method, headers={
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "PEGASUS-Valhalla-Hydrogen-Watch/2.0",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read()
        return json.loads(raw.decode()) if raw else {}

def git_commit(path, content, message):
    try:
        existing = api("GET", f"/repos/{REPO}/contents/{urllib.parse.quote(path)}")
        payload = {"message": message, "content": __import__("base64").b64encode(content.encode()).decode(), "sha": existing["sha"]}
    except Exception:
        payload = {"message": message, "content": __import__("base64").b64encode(content.encode()).decode()}
    api("PUT", f"/repos/{REPO}/contents/{urllib.parse.quote(path)}", payload)

def main():
    now = datetime.now(timezone.utc)
    items, errors = scan()
    seen = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else []
    seen_set = set(seen)
    new = [x for x in items if x["id"] not in seen_set]
    seen = list(dict.fromkeys(seen + [x["id"] for x in items]))[-10000:]
    STATE_FILE.write_text(json.dumps(seen, indent=2))

    lines = [
        "# VALHALLA HYDROGEN REPORT",
        "",
        f"**Automated scan:** {now.isoformat()}",
        f"**New items:** {len(new)}",
        f"**Total items scanned:** {len(items)}",
        "",
        "PEGASUS automatically scans hydrogen intelligence sources. Source claims require verification before being treated as established technical fact.",
        "",
    ]
    for x in new[:100]:
        lines += [f"## {x['title']}", f"- **Source:** {x['source']}", f"- **Published:** {x['published']}", f"- **Category:** {x['category']}", f"- **Valhalla relevance:** {x['relevance']}", f"- **Link:** {x['link']}", f"- **Lead:** {x['summary']}", ""]
    if errors:
        lines += ["## Source Errors", ""] + [f"- {e}" for e in errors]
    report_path = REPORT_DIR / f"VHR-{now.strftime('%Y-%m-%d-%H%M')}.md"
    REPORT_DIR.mkdir(exist_ok=True)
    report_path.write_text("\n".join(lines))
    git_commit(str(report_path), report_path.read_text(), f"PEGASUS: hydrogen report {now.strftime('%Y-%m-%d %H:%M UTC')}")

    alert_items = [x for x in new if x["relevance"] == "DIRECTLY RELEVANT"]
    if alert_items:
        alert = ["# HYDROGEN ALERT", "", f"**PEGASUS alert:** {now.isoformat()}", "", f"New directly relevant items: {len(alert_items)}", ""]
        for x in alert_items[:25]:
            alert += [f"## {x['title']}", f"- {x['source']} | {x['published']}", f"- {x['link']}", ""]
        git_commit(str(ALERT_FILE), "\n".join(alert), f"PEGASUS: hydrogen alert {now.strftime('%Y-%m-%d %H:%M UTC')}")
        # Create a GitHub issue so the repository notification system can surface the alert.
        try:
            api("POST", f"/repos/{REPO}/issues", {"title": f"HYDROGEN ALERT - {now.strftime('%Y-%m-%d %H:%M UTC')}", "body": "\n".join(alert), "labels": ["hydrogen-alert"]})
        except Exception as e:
            print(f"Alert issue creation skipped: {e}")

    # Keep the state file current in GitHub even when no new report file is generated by a separate API commit.
    git_commit(str(STATE_FILE), STATE_FILE.read_text(), f"PEGASUS: update hydrogen watch state {now.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"PEGASUS hydrogen watch complete: {len(new)} new items, {len(alert_items)} direct alerts, {len(errors)} feed errors.")

if __name__ == "__main__":
    main()
