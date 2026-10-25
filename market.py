"""ดึงราคาทอง / DXY / US10Y"""
import time
import requests
import pandas as pd

from . import config

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}

YAHOO_TF = {  # interval, range
    "D1": ("1d", "2y"),
    "H1": ("60m", "60d"),
    "M30": ("30m", "20d"),
    "M15": ("15m", "10d"),
}
TD_TF = {"D1": "1day", "H4": "4h", "H1": "1h", "M30": "30min", "M15": "15min"}


def _get(url, params=None, tries=3):
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=20)
            if r.status_code == 200:
                return r
            last = f"HTTP {r.status_code}"
        except requests.RequestException as e:
            last = str(e)
        time.sleep(2 * (i + 1))
    raise RuntimeError(f"ดึงข้อมูลไม่สำเร็จ {url}: {last}")


def yahoo(symbol, interval, rng):
    hosts = ["https://query1.finance.yahoo.com", "https://query2.finance.yahoo.com"]
    err = None
    for h in hosts:
        try:
            r = _get(f"{h}/v8/finance/chart/{symbol}", {"interval": interval, "range": rng, "includePrePost": "false"})
            res = r.json()["chart"]["result"][0]
            q = res["indicators"]["quote"][0]
            df = pd.DataFrame(
                {k: q[k] for k in ["open", "high", "low", "close", "volume"]},
                index=pd.to_datetime(res["timestamp"], unit="s", utc=True),
            ).dropna(subset=["close"])
            return df
        except Exception as e:  # noqa
            err = e
    raise RuntimeError(f"Yahoo {symbol}: {err}")


def twelvedata(symbol, interval, size=500):
    r = _get("https://api.twelvedata.com/time_series", {
        "symbol": symbol, "interval": interval, "outputsize": size,
        "timezone": "UTC", "apikey": config.TWELVEDATA_API_KEY,
    })
    js = r.json()
    if js.get("status") != "ok":
        raise RuntimeError(f"TwelveData: {js.get('message')}")
    df = pd.DataFrame(js["values"])
    df.index = pd.to_datetime(df["datetime"], utc=True)
    df = df[["open", "high", "low", "close"]].astype(float).sort_index()
    df["volume"] = 0.0
    return df


def resample(df, rule):
    return df.resample(rule, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    ).dropna(subset=["close"])


def gold_frames():
    """คืนค่า (dict ของ DataFrame ต่อ timeframe, ชื่อแหล่งข้อมูล)"""
    if config.TWELVEDATA_API_KEY:
        try:
            frames = {}
            for tf, iv in TD_TF.items():
                frames[tf] = twelvedata("XAU/USD", iv)
                time.sleep(1)  # free plan: 8 requests/นาที
            return frames, "Twelve Data XAU/USD (Spot)"
        except Exception as e:
            print("[warn] Twelve Data ใช้ไม่ได้ -> ใช้ Yahoo แทน:", e)
    frames = {tf: yahoo("GC=F", *YAHOO_TF[tf]) for tf in YAHOO_TF}
    frames["H4"] = resample(frames["H1"], "4h")
    frames = {tf: frames[tf] for tf in config.TIMEFRAMES}
    return frames, "Yahoo GC=F (COMEX Futures — สูงกว่า Spot เล็กน้อย)"


def intermarket():
    """DXY และ US10Y — ถ้าดึงไม่ได้คืน None"""
    out = {}
    for name, sym in [("DXY", "DX-Y.NYB"), ("US10Y", "^TNX")]:
        try:
            df = yahoo(sym, "60m", "5d")
            last = df["close"].iloc[-1]
            h1 = df["close"].iloc[-2] if len(df) > 1 else last
            d1 = df["close"].iloc[-25] if len(df) > 25 else df["close"].iloc[0]
            out[name] = {"last": float(last), "chg_1h": float(last - h1), "chg_24h": float(last - d1)}
        except Exception as e:
            print(f"[warn] {name}:", e)
            out[name] = None
    return out
