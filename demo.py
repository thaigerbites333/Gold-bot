"""ข้อมูลจำลอง สำหรับทดสอบโปรแกรมโดยไม่ต้องต่ออินเทอร์เน็ต (python main.py report --demo)"""
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from market import resample
from news_guide import guide_event


def _walk(n, start, vol, drift, seed, freq):
    rng = np.random.default_rng(seed)
    end = pd.Timestamp.now(tz="UTC").floor(freq)
    idx = pd.date_range(end=end, periods=n, freq=freq)
    c = start + np.cumsum(rng.normal(drift, vol, n))
    o = np.r_[start, c[:-1]]
    h = np.maximum(o, c) + rng.uniform(0, vol * 0.8, n)
    l = np.minimum(o, c) - rng.uniform(0, vol * 0.8, n)
    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "volume": 0.0}, index=idx)


def frames():
    m15 = _walk(4 * 24 * 40, 4020, 2.2, 0.035, 7, "15min")
    return {
        "D1": _walk(400, 3300, 28, 1.8, 3, "1D").pipe(lambda d: d + (m15.close.iloc[-1] - d.close.iloc[-1])),
        "H4": resample(m15, "4h"),
        "H1": resample(m15, "1h"),
        "M30": resample(m15, "30min"),
        "M15": m15,
    }, "DEMO (ข้อมูลจำลอง)"


def intermarket():
    return {"DXY": {"last": 98.42, "chg_1h": -0.05, "chg_24h": -0.21},
            "US10Y": {"last": 4.12, "chg_1h": 0.004, "chg_24h": -0.03}}


def headlines():
    now = datetime.now(timezone.utc)
    T = [("Gold climbs as dollar slips ahead of Fed decision", "Reuters"),
         ("Central banks buy record gold in third quarter, World Gold Council says", "Kitco"),
         ("Treasury yields rise after strong jobs data", "Reuters"),
         ("Gold eases on profit-taking after hitting record high", "FXStreet"),
         ("Powell signals patience on rate cuts amid sticky inflation", "Reuters"),
         ("Middle East tension lifts safe-haven demand", "Kitco")]
    return [{"title": t, "link": "https://example.com", "source": s, "time": now - timedelta(minutes=25 * i),
             "tag": s} for i, (t, s) in enumerate(T)]


def calendar():
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    evs = [
        {"title": "ISM Services PMI", "time": now - timedelta(minutes=95), "impact": "High",
         "impact_th": "แรง", "forecast": "51.2", "previous": "50.8", "id": "d0"},
        {"title": "Core PCE Price Index m/m", "time": now + timedelta(minutes=40), "impact": "High",
         "impact_th": "แรง", "forecast": "0.2%", "previous": "0.3%", "id": "d1"},
        {"title": "Unemployment Claims", "time": now + timedelta(hours=5), "impact": "Medium",
         "impact_th": "กลาง", "forecast": "225K", "previous": "231K", "id": "d2"},
        {"title": "FOMC Statement", "time": now + timedelta(hours=20), "impact": "High",
         "impact_th": "แรง", "forecast": "", "previous": "", "id": "d3"},
    ]
    for ev in evs:
        ev["guide"] = guide_event(ev["title"], ev["impact"])
    return evs


def week_calendar():
    """ปฏิทินจำลองทั้งสัปดาห์ (เวลา 05:30 LA ประมาณข่าวสหรัฐ)"""
    from config import TZ_LOCAL
    base = datetime.now(TZ_LOCAL).replace(hour=5, minute=30, second=0, microsecond=0)
    plan = [(1, "ISM Manufacturing PMI", "High", "49.5", "49.1", 7), (2, "JOLTS Job Openings", "High", "7.40M", "7.23M", 7),
            (3, "ADP Non-Farm Employment Change", "High", "120K", "98K", 5.25), (3, "FOMC Statement", "High", "", "", 11),
            (3, "FOMC Press Conference", "High", "", "", 11.5), (4, "Unemployment Claims", "Medium", "228K", "225K", 5.5),
            (5, "Non-Farm Employment Change", "High", "140K", "122K", 5.5), (5, "Unemployment Rate", "High", "4.2%", "4.2%", 5.5),
            (5, "Average Hourly Earnings m/m", "High", "0.3%", "0.4%", 5.5)]
    evs = []
    for i, (d, t, imp, fc, pv, h) in enumerate(plan):
        tm = (base + timedelta(days=d)).replace(hour=int(h), minute=int((h % 1) * 60))
        evs.append({"title": t, "time": tm.astimezone(timezone.utc), "impact": imp, "impact_th": imp,
                    "forecast": fc, "previous": pv, "id": f"w{i}", "guide": guide_event(t, imp)})
    return evs
