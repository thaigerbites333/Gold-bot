"""คู่มือข่าว: ข่าวนี้คืออะไร แรงแค่ไหน ถ้าออกมาแบบไหนทองจะขึ้น/ลง เพราะอะไร

direction = ผลต่อ "ทอง" เมื่อตัวเลขออกมา "สูงกว่าคาด"
  -1 = สูงกว่าคาด → ทองลง (ดอลลาร์แข็ง)   +1 = สูงกว่าคาด → ทองขึ้น
"""
import re

import pandas as pd

# (คำค้นในชื่อข่าว, ชื่อไทย, ดาวความแรง 1-5, direction, เหตุผลสั้น)
EVENTS = [
    (r"\badp\b", "การจ้างงานภาคเอกชน ADP", 3, -1, "จ้างงานเอกชนดี → ใช้ดูทิศทาง NFP ล่วงหน้า → ดอลลาร์แข็ง"),
    (r"non-farm employment change|nonfarm payroll|\bnfp\b", "การจ้างงานนอกภาคเกษตร (NFP)", 5, -1,
     "จ้างงานดี → เศรษฐกิจแข็ง → Fed ไม่รีบลดดอกเบี้ย → ดอลลาร์แข็ง"),
    (r"unemployment rate", "อัตราว่างงาน", 4, +1, "ว่างงานสูง → เศรษฐกิจอ่อน → คาด Fed ลดดอกเบี้ย"),
    (r"unemployment claims|jobless claims", "ผู้ขอรับสวัสดิการว่างงาน (รายสัปดาห์)", 3, +1,
     "คนตกงานเพิ่ม → เศรษฐกิจอ่อน → คาด Fed ลดดอกเบี้ย"),
    (r"average hourly earnings", "ค่าจ้างเฉลี่ยรายชั่วโมง", 4, -1, "ค่าจ้างขึ้น → เงินเฟ้อค้าง → Fed คุมเข้ม"),
    (r"jolts", "ตำแหน่งงานว่าง JOLTS", 3, -1, "ตลาดแรงงานตึงตัว → Fed คุมเข้ม"),
    (r"core cpi", "เงินเฟ้อพื้นฐาน (Core CPI)", 5, -1, "เงินเฟ้อสูง → Fed ไม่ลด/ขึ้นดอกเบี้ย → ยีลด์+ดอลลาร์ขึ้น"),
    (r"\bcpi\b", "เงินเฟ้อผู้บริโภค (CPI)", 5, -1, "เงินเฟ้อสูง → Fed คุมเข้ม → ดอลลาร์แข็ง"),
    (r"core pce", "เงินเฟ้อ PCE พื้นฐาน (ตัวที่ Fed ใช้)", 4, -1, "เงินเฟ้อสูง → Fed คุมเข้ม"),
    (r"\bpce\b", "เงินเฟ้อ PCE", 3, -1, "เงินเฟ้อสูง → Fed คุมเข้ม"),
    (r"\bppi\b", "เงินเฟ้อผู้ผลิต (PPI)", 3, -1, "ต้นทุนผู้ผลิตขึ้น → เงินเฟ้ออาจตามมา"),
    (r"federal funds rate|fomc statement", "ประกาศดอกเบี้ย Fed (FOMC)", 5, -1,
     "ขึ้น/คงดอกเบี้ยสูงกว่าคาด หรือน้ำเสียงแข็งกร้าว → ดอลลาร์แข็ง"),
    (r"fomc press conference", "แถลงข่าวประธาน Fed หลังประชุม", 5, 0,
     "พูดแนวผ่อนคลาย (dovish) → ทองขึ้น · พูดแนวคุมเข้ม (hawkish) → ทองลง"),
    (r"fomc meeting minutes", "รายงานการประชุม Fed", 4, 0, "เนื้อหา dovish → ทองขึ้น · hawkish → ทองลง"),
    (r"powell|fed chair", "ประธาน Fed พูด", 4, 0, "dovish → ทองขึ้น · hawkish → ทองลง"),
    (r"fomc member|fed .* speaks|speaks", "กรรมการ Fed พูด", 2, 0, "dovish → ทองขึ้น · hawkish → ทองลง"),
    (r"gdp", "GDP เศรษฐกิจสหรัฐ", 4, -1, "เศรษฐกิจโตดี → Fed ไม่รีบลดดอกเบี้ย"),
    (r"core retail sales|retail sales", "ยอดค้าปลีก", 4, -1, "คนใช้จ่ายเยอะ → เศรษฐกิจแข็ง → ดอลลาร์แข็ง"),
    (r"ism services|ism non-manufacturing", "ISM ภาคบริการ", 4, -1, "ภาคบริการแข็ง → เศรษฐกิจแข็ง"),
    (r"ism manufacturing", "ISM ภาคการผลิต", 3, -1, "ภาคการผลิตแข็ง → เศรษฐกิจแข็ง"),
    (r"pmi", "ดัชนี PMI", 2, -1, "ธุรกิจขยายตัว → เศรษฐกิจแข็ง"),
    (r"inflation expectations", "คาดการณ์เงินเฟ้อผู้บริโภค", 3, -1, "คาดเงินเฟ้อสูง → Fed คุมเข้ม"),
    (r"consumer sentiment|consumer confidence", "ความเชื่อมั่นผู้บริโภค", 2, -1, "ผู้บริโภคมั่นใจ → เศรษฐกิจแข็ง"),
    (r"durable goods", "ยอดสั่งซื้อสินค้าคงทน", 2, -1, "ธุรกิจลงทุนเพิ่ม → เศรษฐกิจแข็ง"),
    (r"empire state|philly fed|manufacturing index", "ดัชนีการผลิตรายภูมิภาค", 2, -1, "การผลิตดี → เศรษฐกิจแข็ง"),
    (r"housing|home sales|building permits|housing starts", "ข้อมูลภาคอสังหาฯ", 1, -1, "อสังหาฯ ดี → เศรษฐกิจแข็ง"),
]

STRENGTH_TH = {5: "แรงมาก", 4: "แรง", 3: "ปานกลาง", 2: "เบา", 1: "เบามาก"}


def stars(n):
    return "★" * n + "☆" * (5 - n)


def guide_event(title, impact):
    t = title.lower()
    for pat, th, st, d, why in EVENTS:
        if re.search(pat, t):
            break
    else:
        th, st, d, why = title, (4 if impact == "High" else 2), -1, "ข้อมูลเศรษฐกิจดี → ดอลลาร์แข็ง"
    if impact == "High":
        st = max(st, 4)
    if d == 0:
        scenario_up, scenario_dn = "พูด dovish (เน้นลดดอกเบี้ย)", "พูด hawkish (เน้นคุมเงินเฟ้อ)"
    elif d < 0:
        scenario_up, scenario_dn = "ออกมา <b>ต่ำกว่า</b>คาด", "ออกมา <b>สูงกว่า</b>คาด"
    else:
        scenario_up, scenario_dn = "ออกมา <b>สูงกว่า</b>คาด", "ออกมา <b>ต่ำกว่า</b>คาด"
    return {
        "name_th": th, "stars": st, "strength": STRENGTH_TH[st], "star_txt": stars(st), "why": why,
        "if_up": scenario_up, "if_down": scenario_dn,
        "swing": {5: "$15–40+", 4: "$8–20", 3: "$4–10", 2: "$2–5", 1: "< $3"}[st],
    }


def scenario_text(ev):
    g = ev["guide"]
    fc = f" (คาด {ev['forecast']}, ก่อนหน้า {ev['previous']})" if ev.get("forecast") else ""
    return (f"{g['if_up']} → ทอง <span class='arrow-up'>▲ ขึ้น</span> · {g['if_down']} → ทอง "
            f"<span class='arrow-dn'>▼ ลง</span>{fc}")


def reaction(ev, m15, atr_m15):
    """ผลจริงหลังข่าวออก ดูจากราคาทองแท่ง M15 ที่ข่าวออก"""
    after = m15[m15.index >= pd.Timestamp(ev["time"]).floor("15min")]
    if after.empty:
        return None
    bar = after.iloc[0]
    first = float(bar["close"] - bar["open"])
    since = float(m15["close"].iloc[-1] - bar["open"])
    big = abs(first) >= 1.5 * atr_m15
    if abs(first) < 0.5 * atr_m15:
        verdict = "ตลาดตอบรับเบา ๆ — ตัวเลขน่าจะใกล้เคียงคาด"
    elif first > 0:
        verdict = "ทองพุ่งขึ้น → ตลาดมองว่าข่าว <b>แย่ต่อดอลลาร์ / ดีต่อทอง</b>"
    else:
        verdict = "ทองร่วงลง → ตลาดมองว่าข่าว <b>ดีต่อดอลลาร์ / กดดันทอง</b>"
    return {"first": first, "since": since, "big": big, "verdict": verdict}


# ---------- หัวข่าว: เหตุผลว่าทำไมหนุน/กดดันทอง ----------
THEMES = [
    (+1, ["rate cut", "cuts rates", "dovish", "easing"], "คาด Fed ลดดอกเบี้ย → ดอลลาร์/ยีลด์ลง → หนุนทอง"),
    (+1, ["geopolitic", "war", "tension", "conflict", "missile", "attack", "invasion", "sanction", "nuclear"],
     "ความเสี่ยงภูมิรัฐศาสตร์ → แห่ซื้อสินทรัพย์ปลอดภัย → หนุนทอง"),
    (+1, ["safe haven", "safe-haven", "uncertainty"], "ตลาดกังวล → แรงซื้อทองเป็นที่หลบภัย"),
    (+1, ["tariff", "trade war"], "สงครามการค้า/ภาษี → ความไม่แน่นอนเพิ่ม → หนุนทอง"),
    (+1, ["dollar falls", "dollar slips", "weaker dollar", "dollar weakens", "dollar drops"], "ดอลลาร์อ่อน → หนุนทอง"),
    (+1, ["yields fall", "yields drop", "yields slip"], "บอนด์ยีลด์ลง → ต้นทุนถือทองต่ำลง → หนุนทอง"),
    (+1, ["central bank buying", "central banks buy", "inflows", "etf buying"], "ธนาคารกลาง/กองทุนซื้อทอง → ดีมานด์เพิ่ม"),
    (+1, ["recession", "unemployment rises", "jobless claims rise", "soft data", "weak jobs"],
     "เศรษฐกิจสหรัฐอ่อน → คาด Fed ลดดอกเบี้ย → หนุนทอง"),
    (+1, ["gold rises", "gold gains", "gold climbs", "gold jumps", "gold rallies", "record high", "all-time high"],
     "โมเมนตัมทองยังเป็นขาขึ้น"),
    (-1, ["rate hike", "hikes rates", "hawkish", "higher for longer"], "Fed ส่งสัญญาณคุมเข้ม → ดอลลาร์/ยีลด์ขึ้น → กดดันทอง"),
    (-1, ["strong dollar", "dollar rises", "dollar gains", "dollar firms", "dollar jumps"], "ดอลลาร์แข็ง → กดดันทอง"),
    (-1, ["yields rise", "yields climb", "yields jump"], "บอนด์ยีลด์ขึ้น → กดดันทอง"),
    (-1, ["strong jobs", "hot inflation", "inflation accelerates", "sticky inflation"],
     "ตัวเลขเศรษฐกิจ/เงินเฟ้อแรง → Fed ไม่รีบลดดอกเบี้ย → กดดันทอง"),
    (-1, ["ceasefire", "truce", "peace deal", "risk-on"], "ความเสี่ยงลดลง → เงินไหลออกจากทองไปหุ้น"),
    (-1, ["outflows"], "เงินไหลออกจากกองทุนทอง"),
    (-1, ["gold falls", "gold slips", "gold drops", "gold eases", "gold slides", "profit-taking", "profit taking"],
     "แรงขายทำกำไร / โมเมนตัมทองอ่อนลง"),
]


def _has(t, k):
    return re.search(r"\b" + re.escape(k) + r"\w{0,3}\b", t) is not None


def explain_headline(title, urgent=False):
    t = title.lower()
    score, reasons = 0, []
    for d, kws, why in THEMES:
        if any(_has(t, k) for k in kws):
            score += d
            if why not in reasons:
                reasons.append(why)
    a = abs(score)
    strength = "แรง" if (urgent or a >= 2) else ("ปานกลาง" if a == 1 else "เบา")
    return score, reasons[:2], strength
