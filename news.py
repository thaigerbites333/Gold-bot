"""ข่าวทอง (RSS) + ปฏิทินข่าวเศรษฐกิจ USD"""
import hashlib
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

import requests

from market import UA
from news_guide import explain_headline, guide_event

FEEDS = [
    ("Reuters", "site:reuters.com gold OR bullion"),
    ("Kitco", "site:kitco.com gold"),
    ("ทอง", "gold price OR XAUUSD"),
    ("Fed/USD", "Federal Reserve OR Powell OR \"US dollar\" OR Treasury yields"),
    ("World Gold Council", "\"World Gold Council\" OR \"central bank gold\""),
]
EXTRA_RSS = [
    ("FXStreet", "https://www.fxstreet.com/rss/news"),
]
CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
CALENDAR_NEXT_URL = "https://nfs.faireconomy.media/ff_calendar_nextweek.json"

URGENT = ["emergency", "fed decision", "rate decision", "powell", "war", "missile", "attack", "invasion",
          "nuclear", "sanction", "tariff", "default", "bank collapse", "flash crash"]
TH_IMPACT = {"High": "แรง", "Medium": "กลาง", "Low": "ต่ำ"}


def _gnews_url(q, days=1):
    return f"https://news.google.com/rss/search?q={quote_plus(q + f' when:{days}d')}&hl=en-US&gl=US&ceid=US:en"


def _parse_rss(text, tag):
    items = []
    root = ET.fromstring(text)
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        src = it.find("source")
        source = src.text.strip() if src is not None and src.text else tag
        try:
            dt = parsedate_to_datetime(it.findtext("pubDate")).astimezone(timezone.utc)
        except Exception:
            dt = None
        # Google News ใส่ " - Reuters" ท้ายหัวข้อ
        title = re.sub(r"\s+-\s+[^-]{2,40}$", "", title)
        items.append({"title": title, "link": link, "source": source, "time": dt, "tag": tag})
    return items


def _has(t, k):
    return re.search(r"\b" + re.escape(k) + r"\w{0,3}\b", t) is not None


def score_headline(t):
    return explain_headline(t)[0]


def fetch_headlines(hours=12, limit=12):
    days = max(1, -(-hours // 24))
    allitems = []
    for tag, q in FEEDS:
        try:
            r = requests.get(_gnews_url(q, days), headers=UA, timeout=20)
            allitems += _parse_rss(r.text, tag)
        except Exception as e:
            print(f"[warn] news {tag}:", e)
    for tag, url in EXTRA_RSS:
        try:
            r = requests.get(url, headers=UA, timeout=20)
            allitems += [x for x in _parse_rss(r.text, tag)
                         if re.search(r"gold|xau|fed|dollar|yield", x["title"], re.I)]
        except Exception as e:
            print(f"[warn] news {tag}:", e)
    return rank_headlines(allitems, hours, limit)


def rank_headlines(allitems, hours=12, limit=12):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    seen, out = set(), []
    for x in sorted(allitems, key=lambda x: x["time"] or cutoff, reverse=True):
        key = re.sub(r"\W+", "", x["title"].lower())[:60]
        if key in seen or (x["time"] and x["time"] < cutoff):
            continue
        seen.add(key)
        x["id"] = hashlib.md5(key.encode()).hexdigest()[:10]
        x["urgent"] = any(_has(x["title"].lower(), k) for k in URGENT)
        x["score"], x["reasons"], x["strength"] = explain_headline(x["title"], x["urgent"])
        out.append(x)
    return out[:limit]


def news_sentiment(items):
    total = sum(x["score"] for x in items)
    bull = sum(1 for x in items if x["score"] > 0)
    bear = sum(1 for x in items if x["score"] < 0)
    if total >= 2:
        label, key = "ข่าวหนุนทองขึ้น", "up"
    elif total <= -2:
        label, key = "ข่าวกดดันทอง", "down"
    else:
        label, key = "ข่าวผสม / เป็นกลาง", "side"
    return {"total": total, "bull": bull, "bear": bear, "label": label, "key": key}


def fetch_calendar(next_week=False):
    """ข่าวเศรษฐกิจ USD (Forex Factory, สัปดาห์ อา.–ส.) — impact High/Medium"""
    out = []
    for url in [CALENDAR_URL] + ([CALENDAR_NEXT_URL] if next_week else []):
        try:
            r = requests.get(url, headers=UA, timeout=20)
            out += parse_calendar(r.json())
        except Exception as e:
            print("[warn] calendar:", url, e)
    seen, uniq = set(), []
    for ev in sorted(out, key=lambda x: x["time"]):
        if ev["id"] not in seen:
            seen.add(ev["id"])
            uniq.append(ev)
    return uniq or None


def parse_calendar(data):
    out = []
    for ev in data:
        if ev.get("country") != "USD" or ev.get("impact") not in ("High", "Medium"):
            continue
        try:
            dt = datetime.fromisoformat(ev["date"]).astimezone(timezone.utc)
        except Exception:
            continue
        out.append({"title": ev.get("title", ""), "time": dt, "impact": ev["impact"],
                    "impact_th": TH_IMPACT.get(ev["impact"], ev["impact"]),
                    "forecast": ev.get("forecast", ""), "previous": ev.get("previous", ""),
                    "id": hashlib.md5((ev.get("title", "") + ev["date"]).encode()).hexdigest()[:10],
                    "guide": guide_event(ev.get("title", ""), ev["impact"])})
    return sorted(out, key=lambda e: e["time"])


def upcoming(events, now=None, hours=24, past_hours=6):
    """ข่าวตั้งแต่ past_hours ที่แล้ว ถึง hours ข้างหน้า"""
    now = now or datetime.now(timezone.utc)
    return [e for e in (events or []) if now - timedelta(hours=past_hours) <= e["time"] <= now + timedelta(hours=hours)]
