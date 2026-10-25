"""อินดิเคเตอร์ + วิเคราะห์เทรนด์แบบ Top-down (D1 → H4 → H1 → M30 → M15)

ใช้สูตรเดียวกับไฟล์ tradingview/gold_topdown.pine เพื่อให้ผลตรงกับกราฟ
"""
import numpy as np
import pandas as pd

from . import config


# ---------------- Indicators ----------------
def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def rsi(s, n=14):
    d = s.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50)


def macd(s, f=12, sl=26, sig=9):
    m = ema(s, f) - ema(s, sl)
    sg = ema(m, sig)
    return m, sg, m - sg


def atr(df, n=14):
    pc = df["close"].shift()
    tr = pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(), (df["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def add_indicators(df):
    df = df.copy()
    c = df["close"]
    df["ema20"], df["ema50"], df["ema200"] = ema(c, 20), ema(c, 50), ema(c, 200)
    df["rsi"] = rsi(c)
    df["macd"], df["signal"], df["hist"] = macd(c)
    df["atr"] = atr(df)
    return df


# ---------------- Trend per timeframe ----------------
LABELS = [(3, "ขาขึ้นแรง", "up2"), (1, "ขาขึ้น", "up"), (-1, "ไซด์เวย์", "side"),
          (-3, "ขาลง", "down"), (-99, "ขาลงแรง", "down2")]


def label_of(score):
    for th, th_label, key in LABELS:
        if score >= th:
            return th_label, key
    return "ขาลงแรง", "down2"


def tf_trend(df):
    r = df.iloc[-1]
    s = 0
    s += 1 if r["close"] > r["ema50"] else -1
    s += 1 if r["ema20"] > r["ema50"] else -1
    s += 1 if r["ema50"] > r["ema200"] else -1
    s += 1 if r["hist"] > 0 else -1
    s += 1 if r["rsi"] > 55 else (-1 if r["rsi"] < 45 else 0)
    label, key = label_of(s)
    return {
        "score": int(s), "label": label, "key": key,
        "close": float(r["close"]), "ema20": float(r["ema20"]), "ema50": float(r["ema50"]), "ema200": float(r["ema200"]),
        "rsi": float(r["rsi"]), "hist": float(r["hist"]), "atr": float(r["atr"]),
    }


# ---------------- Levels ----------------
def swing_levels(df, left=3, right=3, lookback=150):
    d = df.tail(lookback)
    hi, lo = d["high"].values, d["low"].values
    highs, lows = [], []
    for i in range(left, len(d) - right):
        if hi[i] == max(hi[i - left:i + right + 1]):
            highs.append(float(hi[i]))
        if lo[i] == min(lo[i - left:i + right + 1]):
            lows.append(float(lo[i]))
    return highs, lows


def nearest(levels, price, above=True, n=2, min_gap=0.0):
    c = sorted({round(x, 2) for x in levels if (x > price + min_gap if above else x < price - min_gap)},
               reverse=not above)
    out = []
    for x in c:  # รวมแนวที่ใกล้กันเกินไป
        if not out or abs(x - out[-1]) > min_gap * 2:
            out.append(x)
        if len(out) == n:
            break
    return out


def daily_pivots(d1):
    p = d1.iloc[-2]  # แท่งวันก่อนหน้า (ปิดแล้ว)
    P = (p.high + p.low + p.close) / 3
    return {"P": P, "R1": 2 * P - p.low, "S1": 2 * P - p.high,
            "R2": P + (p.high - p.low), "S2": P - (p.high - p.low),
            "PDH": float(p.high), "PDL": float(p.low)}


# ---------------- Main analysis ----------------
def analyze(frames):
    frames = {tf: add_indicators(df) for tf, df in frames.items()}
    trends = {tf: tf_trend(frames[tf]) for tf in config.TIMEFRAMES}
    bias = sum(trends[tf]["score"] * w for tf, w in config.TF_WEIGHT.items())  # -5..+5
    bias_label, bias_key = label_of(bias)

    m15 = frames["M15"]
    price = float(m15["close"].iloc[-1])
    atr_m15 = trends["M15"]["atr"]
    atr_h1 = trends["H1"]["atr"]

    hs, ls = swing_levels(frames["H1"])
    gap = max(atr_m15 * 0.5, 0.5)
    res = nearest(hs, price, True, 3, gap)
    sup = nearest(ls, price, False, 3, gap)
    piv = daily_pivots(frames["D1"])

    # การเปลี่ยนแปลงราคา
    h1 = frames["H1"]["close"]
    d1 = frames["D1"]["close"]
    chg = {"1h": price - float(h1.iloc[-2]), "24h": price - float(d1.iloc[-2])}
    day = frames["D1"].iloc[-1]

    big = (trends["D1"]["score"] + trends["H4"]["score"])   # เทรนด์ใหญ่
    small = (trends["M15"]["score"] + trends["M30"]["score"])
    plan = build_plan(price, bias, big, small, sup, res, atr_m15, trends)

    return {
        "price": price, "chg": chg, "day_high": float(day.high), "day_low": float(day.low),
        "trends": trends, "bias": bias, "bias_label": bias_label, "bias_key": bias_key,
        "support": sup, "resistance": res, "pivots": piv,
        "atr_m15": atr_m15, "atr_h1": atr_h1, "plan": plan, "frames": frames,
        "last_h1_range": float(frames["H1"]["high"].iloc[-1] - frames["H1"]["low"].iloc[-1]),
    }


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def build_plan(price, bias, big, small, sup, res, atr_m15, trends):
    pv = config.POINT_VALUE
    tp1, tp2 = config.TP_POINTS[0] * pv, config.TP_POINTS[1] * pv
    s1 = sup[0] if sup else price - atr_m15 * 2
    r1 = res[0] if res else price + atr_m15 * 2
    ema_zone = (trends["M15"]["ema20"], trends["M15"]["ema50"])

    if bias >= 1 and big > 0:
        side = "BUY"
        entry = f"รอย่อลงมาแถว EMA20–50 ของ M15 ({min(ema_zone):.2f}–{max(ema_zone):.2f}) หรือแนวรับ {s1:.2f}"
        e = min(max(ema_zone), price)
        sl_dist = _clamp(e - min(s1, e) + atr_m15 * 0.3, tp1 * 0.75, tp2 * 1.5)
        sl, t1, t2 = e - sl_dist, e + tp1, e + tp2
        why = "เทรนด์ใหญ่ (D1/H4) เป็นขาขึ้น — เน้นซื้อตามน้ำ ไม่สวนเทรนด์"
        if small < 0:
            why += " · ตอนนี้ M15/M30 กำลังย่อ รอสัญญาณกลับตัวขึ้นก่อนเข้า"
    elif bias <= -1 and big < 0:
        side = "SELL"
        entry = f"รอเด้งขึ้นไปแถว EMA20–50 ของ M15 ({min(ema_zone):.2f}–{max(ema_zone):.2f}) หรือแนวต้าน {r1:.2f}"
        e = max(min(ema_zone), price)
        sl_dist = _clamp(max(r1, e) - e + atr_m15 * 0.3, tp1 * 0.75, tp2 * 1.5)
        sl, t1, t2 = e + sl_dist, e - tp1, e - tp2
        why = "เทรนด์ใหญ่ (D1/H4) เป็นขาลง — เน้นขายตามน้ำ ไม่สวนเทรนด์"
        if small > 0:
            why += " · ตอนนี้ M15/M30 กำลังเด้ง รอสัญญาณกลับตัวลงก่อนเข้า"
    else:
        side = "WAIT"
        entry = f"ราคาอยู่ในกรอบ {s1:.2f} – {r1:.2f} · เทรดสั้นที่ขอบกรอบเท่านั้น หรือรอเบรกให้ชัด"
        e = price
        sl, t1, t2, sl_dist = None, None, None, 0
        why = "เทรนด์ใหญ่กับเทรนด์เล็กยังไม่ไปทางเดียวกัน — ความเสี่ยงสูง ควรรอ"
    rr = (tp2 / sl_dist) if sl_dist else None
    return {"rr": rr, "side": side, "entry_text": entry, "entry": e, "sl": sl, "tp1": t1, "tp2": t2,
            "why": why, "sl_dist": sl_dist, "s1": s1, "r1": r1}
