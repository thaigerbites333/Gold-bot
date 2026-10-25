"""สรุปประจำสัปดาห์ (ส่งวันอาทิตย์ก่อนเที่ยง LA — ก่อนตลาดเปิด 15:00 LA)

- ทองสัปดาห์ที่แล้วเป็นยังไง
- เทรนด์ใหญ่ W1 / D1 / H4 → มุมมองสัปดาห์หน้า
- แนวรับ-ต้านสำคัญ + Pivot รายสัปดาห์ + กรอบที่คาดว่าจะวิ่ง
- ปฏิทินข่าว USD ทั้งสัปดาห์ แยกรายวัน พร้อมบอกว่าออกแบบไหนทองขึ้น/ลง
- ธีมข่าวที่ตลาดสนใจ
"""
from collections import Counter, OrderedDict
from datetime import datetime, timedelta, timezone

import config
from analysis import add_indicators, label_of, nearest, swing_levels, tf_trend
from charts import candle_chart
from news_guide import scenario_text
from report import CSS, e, sgn, tdt

TH_DAY_FULL = ["วันจันทร์", "วันอังคาร", "วันพุธ", "วันพฤหัสบดี", "วันศุกร์", "วันเสาร์", "วันอาทิตย์"]
TH_MONTH = ["", "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]
W_WEIGHT = {"W1": 0.40, "D1": 0.40, "H4": 0.20}


def weekly_bars(d1):
    # สัปดาห์ทองปิดวันศุกร์
    return d1.resample("W-FRI", label="right", closed="right").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna(subset=["close"])


def analyze_week(frames):
    w1 = add_indicators(weekly_bars(frames["D1"]))
    d1 = add_indicators(frames["D1"])
    h4 = add_indicators(frames["H4"])
    tr = {"W1": tf_trend(w1), "D1": tf_trend(d1), "H4": tf_trend(h4)}
    bias = sum(tr[k]["score"] * w for k, w in W_WEIGHT.items())
    bias_label, bias_key = label_of(bias)

    price = float(h4["close"].iloc[-1])
    lw = w1.iloc[-1]  # สัปดาห์ล่าสุด (ปิดศุกร์)
    pw = w1.iloc[-2]
    P = (lw.high + lw.low + lw.close) / 3
    piv = {"R2": P + (lw.high - lw.low), "R1": 2 * P - lw.low, "P": P,
           "S1": 2 * P - lw.high, "S2": P - (lw.high - lw.low)}
    atr_w = float(w1["atr"].iloc[-1])
    atr_d = float(d1["atr"].iloc[-1])

    hs, ls = swing_levels(d1, 3, 3, 120)
    gap = max(atr_d * 0.3, 2)
    res = nearest(hs, price, True, 3, gap)
    sup = nearest(ls, price, False, 3, gap)

    # สัปดาห์ที่แล้วเป็นยังไง
    recap = {"open": float(lw.open), "close": float(lw.close), "high": float(lw.high), "low": float(lw.low),
             "chg": float(lw.close - pw.close), "pct": float((lw.close / pw.close - 1) * 100),
             "range": float(lw.high - lw.low)}

    # แผนรายสัปดาห์
    big = tr["W1"]["score"] + tr["D1"]["score"]
    if bias >= 1 and big > 0:
        side, plan = "BUY", (f"เทรนด์ใหญ่ขาขึ้น → เน้น <b>BUY เมื่อย่อ</b> แถวแนวรับ {sup[0] if sup else piv['S1']:,.2f} "
                             f"/ Pivot {piv['P']:,.2f} · หลีกเลี่ยงการ Sell สวนเทรนด์ เว้นแต่หลุด {piv['S1']:,.2f} ชัดเจน")
    elif bias <= -1 and big < 0:
        side, plan = "SELL", (f"เทรนด์ใหญ่ขาลง → เน้น <b>SELL เมื่อเด้ง</b> แถวแนวต้าน {res[0] if res else piv['R1']:,.2f} "
                              f"/ Pivot {piv['P']:,.2f} · หลีกเลี่ยงการ Buy สวนเทรนด์ เว้นแต่ยืนเหนือ {piv['R1']:,.2f} ได้")
    else:
        side, plan = "WAIT", (f"เทรนด์ใหญ่ยังไม่ชัด → เทรดในกรอบ {piv['S1']:,.2f} – {piv['R1']:,.2f} "
                              f"(Buy ใกล้ขอบล่าง / Sell ใกล้ขอบบน) แล้วรอเบรกให้ชัดก่อนตามเทรนด์")
    scen_up = (f"ถ้ายืนเหนือ <b>{piv['R1']:,.2f}</b> ได้ → มีลุ้นไป {piv['R2']:,.2f}"
               + (f" / {res[1]:,.2f}" if len(res) > 1 else ""))
    scen_dn = (f"ถ้าหลุด <b>{piv['S1']:,.2f}</b> → มีโอกาสลงไป {piv['S2']:,.2f}"
               + (f" / {sup[1]:,.2f}" if len(sup) > 1 else ""))

    return {"price": price, "trends": tr, "bias": bias, "bias_label": bias_label, "bias_key": bias_key,
            "pivots": piv, "support": sup, "resistance": res, "atr_w": atr_w, "atr_d": atr_d,
            "recap": recap, "side": side, "plan": plan, "scen_up": scen_up, "scen_dn": scen_dn,
            "range_lo": price - atr_w * 0.6, "range_hi": price + atr_w * 0.6,
            "frames": {"D1": d1, "H4": h4, "W1": w1}}


def week_events(events, now=None):
    now = now or datetime.now(timezone.utc)
    return [x for x in (events or []) if now <= x["time"] <= now + timedelta(days=7)]


def group_by_day(events):
    days = OrderedDict()
    for x in events:
        d = x["time"].astimezone(config.TZ_LOCAL)
        key = f"{TH_DAY_FULL[d.weekday()]} {d.day} {TH_MONTH[d.month]}"
        days.setdefault(key, []).append(x)
    return days


def theme_counts(heads):
    c = Counter()
    for h in heads:
        for r in h.get("reasons", []):
            c[r] += 1
    return c.most_common(5)


def build_weekly_html(w, events, heads, sent, inter, source, ai=None):
    now = datetime.now(timezone.utc)
    t, piv, rc = w["trends"], w["pivots"], w["recap"]
    side_th = {"BUY": "เน้น BUY", "SELL": "เน้น SELL", "WAIT": "เทรดในกรอบ / รอ"}[w["side"]]
    by_day = group_by_day(events)

    # วันไหนต้องระวังสุด
    hot = sorted(((sum(x["guide"]["stars"] for x in evs if x["guide"]["stars"] >= 4), d) for d, evs in by_day.items()),
                 reverse=True)
    hot_days = [d for s, d in hot if s > 0][:2]
    big_events = sorted([x for x in events if x["guide"]["stars"] >= 4], key=lambda x: -x["guide"]["stars"])[:4]

    bullets = []
    bullets.append(f"สัปดาห์ที่แล้วทอง{'ขึ้น' if rc['chg'] >= 0 else 'ลง'} <b>{abs(rc['chg']):,.2f}</b> "
                   f"({rc['pct']:+.2f}%) ปิดที่ {rc['close']:,.2f} · กรอบ {rc['low']:,.2f} – {rc['high']:,.2f}")
    bullets.append(f"เทรนด์ใหญ่: W1 <b>{t['W1']['label']}</b> · D1 <b>{t['D1']['label']}</b> · H4 <b>{t['H4']['label']}</b> "
                   f"→ มุมมองสัปดาห์หน้า <b>{w['bias_label']}</b> ({side_th})")
    bullets.append(f"กรอบที่คาดว่าทองจะวิ่งสัปดาห์นี้ ~<b>{w['range_lo']:,.0f} – {w['range_hi']:,.0f}</b> "
                   f"(ATR รายสัปดาห์ ≈ ${w['atr_w']:,.0f}, รายวัน ≈ ${w['atr_d']:,.0f})")
    if big_events:
        bullets.append("ข่าวใหญ่สัปดาห์นี้: " + " · ".join(
            f"<b>{e(x['guide']['name_th'])}</b> {x['guide']['star_txt']} ({tdt(x['time'])})" for x in big_events))
    if hot_days:
        bullets.append(f"<span class='warn'>วันที่ต้องระวังที่สุด:</span> {' และ '.join(hot_days)}")
    if sent:
        bullets.append(f"ข่าวช่วง 3 วันที่ผ่านมา: <b>{sent['label']}</b> (หนุน {sent['bull']} / กดดัน {sent['bear']})")
    dxy = (inter or {}).get("DXY")
    if dxy:
        bullets.append(f"ดอลลาร์ (DXY) {dxy['last']:.2f} · ล่าสุด {sgn(dxy['chg_24h'])} → "
                       f"{'กดดันทอง' if dxy['chg_24h'] > 0 else 'หนุนทอง'}")
    if ai and ai.get("summary"):
        bullets = [e(b) for b in ai["summary"]] + bullets[3:]

    rows = ""
    for k, nm in [("W1", "รายสัปดาห์"), ("D1", "รายวัน"), ("H4", "4 ชม.")]:
        x = t[k]
        rows += (f"<tr><td><b>{k}</b> <span class='muted'>{nm}</span></td><td><span class='chip {x['key']}'>{x['label']}</span></td>"
                 f"<td class='num'>{x['score']:+d}</td><td class='num'>{x['rsi']:.0f}</td>"
                 f"<td>{'เหนือ' if x['close'] > x['ema50'] else 'ใต้'} EMA50 ({x['ema50']:,.0f})</td></tr>")

    ks = ["R2", "R1", "P", "S1", "S2"]
    pv = ("<tr>" + "".join(f"<th class='num'>{k}</th>" for k in ks) + "</tr><tr>" +
          "".join(f"<td class='num'>{piv[k]:,.2f}</td>" for k in ks) + "</tr>")
    lv = "".join(f"<tr><td class='arrow-dn'>แนวต้าน D1</td><td class='num'>{x:,.2f}</td></tr>" for x in reversed(w["resistance"]))
    lv += f"<tr><td><b>ราคาล่าสุด</b></td><td class='num'><b>{w['price']:,.2f}</b></td></tr>"
    lv += "".join(f"<tr><td class='arrow-up'>แนวรับ D1</td><td class='num'>{x:,.2f}</td></tr>" for x in w["support"])
    lv += (f"<tr><td class='muted'>High/Low สัปดาห์ก่อน</td><td class='num'>{rc['high']:,.2f} / {rc['low']:,.2f}</td></tr>")

    cal = ""
    for day, evs in by_day.items():
        cal += f"<tr><td colspan='4' class='dayhead'>{day}</td></tr>"
        for x in evs:
            g = x["guide"]
            cal += (f"<tr><td style='white-space:nowrap'>{x['time'].astimezone(config.TZ_LOCAL):%H:%M}</td>"
                    f"<td><b>{e(g['name_th'])}</b><div class='muted'>{e(x['title'])}</div></td>"
                    f"<td style='white-space:nowrap'><span class='stars s{g['stars']}'>{g['star_txt']}</span>"
                    f"<div class='muted'>{g['strength']} · สวิง {g['swing']}</div></td>"
                    f"<td>{scenario_text(x)}<div class='why'>{e(g['why'])}</div></td></tr>")
    if not cal:
        cal = "<tr><td colspan='4' class='muted'>ยังไม่มีปฏิทินข่าวสัปดาห์นี้ (หรือดึงไม่ได้)</td></tr>"

    themes = "".join(f"<li>{e(r)} <span class='muted'>({n} ข่าว)</span></li>" for r, n in theme_counts(heads)) \
        or "<li class='muted'>ไม่มีธีมเด่น</li>"
    news_rows = ""
    for h in heads[:8]:
        arrow = ("<span class='arrow-up'>▲</span>" if h["score"] > 0 else
                 "<span class='arrow-dn'>▼</span>" if h["score"] < 0 else "<span class='arrow-0'>●</span>")
        why = f"<div class='why'>{e(' / '.join(h['reasons']))}</div>" if h.get("reasons") else ""
        news_rows += (f"<tr><td>{arrow}</td><td><a href='{e(h['link'])}'>{e(h['title'])}</a>{why}</td>"
                      f"<td class='muted' style='white-space:nowrap'>{e(h['source'])}<br>{tdt(h['time']) if h['time'] else ''}</td></tr>")

    ch_d1 = candle_chart(w["frames"]["D1"], "D1 - last ~4 months", w, bars=90, height=2.8, plan=False)
    ch_w1 = candle_chart(w["frames"]["W1"], "W1 - last ~1 year", w, bars=52, height=2.3, levels=False, plan=False)

    # เวลาตลาดเปิด (อา. 18:00 NY = 15:00 LA)
    ny = now.astimezone(config.TZ_NY)
    open_ny = (ny + timedelta(days=(6 - ny.weekday()) % 7)).replace(hour=18, minute=0, second=0, microsecond=0)
    open_txt = tdt(open_ny)

    return f"""<!doctype html><html lang="th"><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700;800&display=swap" rel="stylesheet">
<title>สรุปทองประจำสัปดาห์</title><style>{CSS}
.dayhead {{ background:#fef3c7; font-weight:700; color:#92400e; padding:3px 6px; }}
.why {{ font-size:9pt; color:#4b5563; margin-top:1px; }}
.stars {{ letter-spacing:1px; color:#d1d5db; }} .stars.s5,.stars.s4 {{ color:#b91c1c; }} .stars.s3 {{ color:#d97706; }} .stars.s2,.stars.s1 {{ color:#6b7280; }}
</style></head><body>
<div class="head"><div><h1><span class="gold">●</span> สรุปทองคำ XAUUSD ประจำสัปดาห์</h1>
<div class="muted">{tdt(now)} น. (เวลา LA) · ตลาดเปิด <b>{open_txt} LA</b> — ระวังราคาเปิด gap · แหล่งราคา: {e(source)}</div></div>
<div class="muted" style="text-align:right"><a href="https://www.tradingview.com/chart/?symbol={config.TRADINGVIEW_SYMBOL}">เปิดกราฟ TradingView ›</a></div></div>

<div class="hero">
  <div class="card"><div class="muted">ปิดสัปดาห์ที่แล้ว</div><div class="big">{rc['close']:,.2f}</div>
    <div>{sgn(rc['chg'])} ({rc['pct']:+.2f}%)</div><div class="muted">กรอบ {rc['low']:,.2f} – {rc['high']:,.2f}</div></div>
  <div class="card"><div class="muted">เทรนด์ใหญ่สัปดาห์หน้า (คะแนน {w['bias']:+.1f} / 5)</div>
    <div style="margin:4px 0"><span class="chip {w['bias_key']}" style="font-size:15pt">{w['bias_label']}</span></div>
    <div class="muted">กรอบคาด ~{w['range_lo']:,.0f} – {w['range_hi']:,.0f}</div></div>
  <div class="card" style="text-align:center"><div class="muted">แผนสัปดาห์นี้</div>
    <div class="side-big {w['side']}" style="margin-top:4px;font-size:17pt">{side_th}</div></div>
</div>

<h2>สรุปง่าย ๆ</h2><ul>{''.join(f'<li>{b}</li>' for b in bullets)}</ul>

<h2>แผนเทรดสัปดาห์นี้</h2>
<div class="plan"><table>
<tr><td>แนวทางหลัก</td><td>{w['plan']}</td></tr>
<tr><td>ฉากทัศน์ขึ้น</td><td class="arrow-up" style="font-weight:400">▲ {w['scen_up']}</td></tr>
<tr><td>ฉากทัศน์ลง</td><td class="arrow-dn" style="font-weight:400">▼ {w['scen_dn']}</td></tr>
<tr><td>วันข่าวแรง</td><td>{' และ '.join(hot_days) if hot_days else '-'} → ลดขนาด lot / งดเข้า 15 นาทีก่อน–หลังข่าว</td></tr>
</table></div>

<h2>เทรนด์ใหญ่ W1 → D1 → H4</h2>
<table><tr><th>TF</th><th>เทรนด์</th><th class="num">คะแนน</th><th class="num">RSI</th><th>ราคา</th></tr>{rows}</table>

<div class="grid2">
  <div><h2>แนวรับ–แนวต้านสำคัญ</h2><table>{lv}</table></div>
  <div><h2>Pivot รายสัปดาห์</h2><table>{pv}</table>
    <h2>ธีมข่าวที่ตลาดสนใจ</h2><ul>{themes}</ul></div>
</div>

<div class="pb"></div>
<h2>ปฏิทินข่าว USD สัปดาห์นี้ — ออกแบบไหน ทองขึ้นหรือลง (เวลา LA)</h2>
<table class="news"><tr><th>เวลา</th><th>ข่าว</th><th>ความแรง</th><th>ผลต่อทอง</th></tr>{cal}</table>
<div class="muted">หลักจำง่าย: ตัวเลขเศรษฐกิจ/เงินเฟ้อสหรัฐ <b>ดีกว่าคาด</b> → ดอลลาร์แข็ง → ทองลง · <b>แย่กว่าคาด</b> → ทองขึ้น
(ยกเว้นอัตราว่างงาน/ผู้ขอสวัสดิการว่างงาน: สูง = ทองขึ้น)</div>

<div class="pb"></div>
<h2>กราฟภาพใหญ่</h2>
<img class="chart" src="{ch_d1}"><img class="chart" src="{ch_w1}">

<h2>ข่าวเด่น 3 วันที่ผ่านมา</h2>
<table class="news">{news_rows or "<tr><td class='muted'>ดึงข่าวไม่ได้</td></tr>"}</table>

<div class="foot">สรุปอัตโนมัติเพื่อช่วยวางแผน ไม่ใช่คำแนะนำการลงทุน · ยืนยันบนกราฟ TradingView ก่อนเข้าออเดอร์ทุกครั้ง</div>
</body></html>"""


def weekly_email(w, events):
    rc = w["recap"]
    side_th = {"BUY": "เน้น BUY เมื่อย่อ", "SELL": "เน้น SELL เมื่อเด้ง", "WAIT": "เทรดในกรอบ / รอ"}[w["side"]]
    big = [x for x in events if x["guide"]["stars"] >= 4][:6]
    items = "".join(f"<li>{tdt(x['time'])} LA — <b>{e(x['guide']['name_th'])}</b> {x['guide']['star_txt']}<br>"
                    f"{scenario_text(x)}</li>" for x in big)
    return (
        "<style>.arrow-up{color:#15803d;font-weight:700}.arrow-dn{color:#b91c1c;font-weight:700}</style>"
        "<div style='font-family:Sarabun,Tahoma,sans-serif;font-size:15px;color:#1f2937'>"
        f"<p style='font-size:20px'><b>สรุปทองประจำสัปดาห์</b></p>"
        f"<p>สัปดาห์ที่แล้ว: ปิด {rc['close']:,.2f} ({sgn(rc['chg'])}, {rc['pct']:+.2f}%)</p>"
        f"<p>เทรนด์ใหญ่: <b>{w['bias_label']}</b> · แผน: <b>{side_th}</b><br>"
        f"W1 {w['trends']['W1']['label']} · D1 {w['trends']['D1']['label']} · H4 {w['trends']['H4']['label']}</p>"
        f"<p>กรอบคาด ~{w['range_lo']:,.0f} – {w['range_hi']:,.0f} · Pivot {w['pivots']['P']:,.2f} "
        f"(R1 {w['pivots']['R1']:,.2f} / S1 {w['pivots']['S1']:,.2f})</p>"
        + (f"<p><b>ข่าวแรงสัปดาห์นี้ (เวลา LA)</b></p><ul>{items}</ul>" if items else "")
        + "<p>ตลาดเปิดวันอาทิตย์ 15:00 LA · รายละเอียดเต็มใน PDF แนบ</p></div>")
