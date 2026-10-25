"""สร้างรายงาน HTML → PDF (ภาษาไทย อ่านง่าย)"""
import html
from datetime import datetime, timezone

import config
from charts import candle_chart
from news_guide import scenario_text

TH_MONTH = ["", "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]
TH_DAY = ["จ.", "อ.", "พ.", "พฤ.", "ศ.", "ส.", "อา."]
TF_TH = {"D1": "รายวัน", "H4": "4 ชม.", "H1": "1 ชม.", "M30": "30 นาที", "M15": "15 นาที"}


def tdt(dt, with_day=True):
    """เวลา LA เสมอ"""
    d = dt.astimezone(config.TZ_LOCAL)
    s = f"{d.day} {TH_MONTH[d.month]} {d:%H:%M}"
    return (TH_DAY[d.weekday()] + " " + s) if with_day else s


def e(x):
    return html.escape(str(x))


def sgn(x, nd=2):
    return f"{x:+,.{nd}f}"


def pts(diff):
    return f"{abs(diff) / config.POINT_VALUE:,.0f}"


def simple_bullets(a, sent, events, inter):
    t = a["trends"]
    out = []
    move = "ขึ้น" if a["chg"]["1h"] >= 0 else "ลง"
    out.append(f"ทองอยู่ที่ <b>{a['price']:,.2f}</b> — {move} {abs(a['chg']['1h']):.2f} ใน 1 ชม. "
               f"({sgn(a['chg']['24h'])} จากเมื่อวาน)")
    out.append(f"เทรนด์ใหญ่ D1 <b>{t['D1']['label']}</b> · H4 <b>{t['H4']['label']}</b> — "
               f"เทรนด์เล็ก M15 <b>{t['M15']['label']}</b>")
    if sent:
        out.append(f"ข่าว: <b>{sent['label']}</b> (หนุน {sent['bull']} ข่าว / กดดัน {sent['bear']} ข่าว)")
    dxy = inter.get("DXY") if inter else None
    if dxy:
        eff = "กดดันทอง" if dxy["chg_24h"] > 0 else "หนุนทอง"
        out.append(f"ดอลลาร์ (DXY) {sgn(dxy['chg_24h'])} ใน 24 ชม. → {eff}")
    out += news_bullets(events)
    return out


def news_bullets(events):
    """ข่าวที่เพิ่งออก + ข่าวแรงถัดไป พร้อมบอกว่าออกแบบไหนทองขึ้น/ลง"""
    now = datetime.now(timezone.utc)
    out = []
    done = [x for x in events if x["time"] <= now and x.get("reaction") and x["guide"]["stars"] >= 3]
    if done:
        x = done[-1]
        r = x["reaction"]
        out.append(f"ข่าวเพิ่งออก <b>{e(x['guide']['name_th'])}</b> ({tdt(x['time'], with_day=False)} LA): "
                   f"ทอง {sgn(r['first'])} ใน 15 นาทีแรก, {sgn(r['since'])} ถึงตอนนี้ — {r['verdict']}")
    soon = [x for x in events if x["time"] > now and x["guide"]["stars"] >= 3
            and (x["time"] - now).total_seconds() <= 6 * 3600]
    if soon:
        x = soon[0]
        g = x["guide"]
        out.append(f"<span class='warn'>ข่าว{g['strength']} {g['star_txt']}</span> <b>{e(g['name_th'])}</b> "
                   f"เวลา {tdt(x['time'], with_day=False)} LA — {scenario_text(x)} · ทองอาจสวิง {g['swing']} "
                   f"· งดเปิดออเดอร์ใหม่ 15 นาทีก่อน–หลังข่าว")
    return out


CSS = """
@page { size: A4; margin: 10mm 11mm; }
* { box-sizing: border-box; }
body { font-family: 'Sarabun', 'Noto Sans Thai', 'Loma', 'Tahoma', sans-serif; color:#1f2937; font-size: 10.5pt;
       margin:0; line-height:1.45; background:#fff; }
h1 { font-size: 19pt; margin:0; }
h2 { font-size: 12pt; margin: 9px 0 4px; padding-bottom:3px; border-bottom: 2px solid #f3e7c4; }
.muted { color:#6b7280; font-size:9.5pt; }
.head { display:flex; justify-content:space-between; align-items:flex-end; border-bottom:3px solid #b8860b; padding-bottom:6px; }
.gold { color:#a16207; }
.hero { display:flex; gap:10px; margin-top:8px; }
.card { border:1px solid #e5e7eb; border-radius:10px; padding:10px 12px; flex:1; }
.big { font-size: 22pt; font-weight:700; line-height:1.1; }
.chip { display:inline-block; padding:1px 9px; border-radius:999px; font-weight:700; font-size:10.5pt; }
.up2,.up { background:#dcfce7; color:#166534; } .down2,.down { background:#fee2e2; color:#991b1b; }
.side { background:#f3f4f6; color:#374151; }
.BUY { background:#15803d; color:#fff; } .SELL { background:#b91c1c; color:#fff; } .WAIT { background:#6b7280; color:#fff; }
.side-big { font-size:22pt; font-weight:800; padding:2px 16px; border-radius:10px; display:inline-block; }
ul { margin:2px 0 0 0; padding-left:18px; } li { margin: 1px 0; }
table { width:100%; border-collapse: collapse; font-size:9.8pt; }
th { text-align:left; color:#6b7280; font-weight:600; border-bottom:1px solid #e5e7eb; padding:2px 6px; }
td { padding:2px 6px; border-bottom:1px solid #f3f4f6; }
td.num, th.num { text-align:right; font-variant-numeric: tabular-nums; }
.plan { border:2px solid #b8860b; background:#fffbeb; border-radius:10px; padding:10px 12px; }
.grid2 { display:grid; grid-template-columns: 1fr 1fr; gap:10px; }
.warn { color:#b91c1c; font-weight:700; }
.chart { width:100%; margin-top:4px; }
.news td { vertical-align:top; }
.arrow-up { color:#15803d; font-weight:800; } .arrow-dn { color:#b91c1c; font-weight:800; } .arrow-0 { color:#9ca3af; }
.pb { page-break-before: always; }
.why { font-size:9pt; color:#4b5563; margin-top:1px; }
.stars { letter-spacing:1px; color:#d1d5db; } .stars.s5,.stars.s4 { color:#b91c1c; } .stars.s3 { color:#d97706; } .stars.s2,.stars.s1 { color:#6b7280; }
a { color:#1d4ed8; text-decoration:none; }
.foot { margin-top:10px; font-size:8.5pt; color:#9ca3af; }
"""


def build_html(a, headlines, sent, events, inter, source, ai=None, urgent_reasons=None, box_title="แจ้งเตือนด่วน"):
    now = datetime.now(timezone.utc)
    t, p = a["trends"], a["plan"]
    bullets = [e(b) for b in (ai or {}).get("summary") or []] or simple_bullets(a, sent, events, inter)
    if urgent_reasons:
        bullets = [b for b in bullets if "class='warn'>ข่าว" not in b]
    if ai and ai.get("summary"):
        bullets = list(bullets) + news_bullets(events)
    if ai and ai.get("watch"):
        bullets = list(bullets) + [f"<span class='warn'>จับตา:</span> {e(ai['watch'])}"]
    th_heads = (ai or {}).get("headlines_th") or []
    tv = f"https://www.tradingview.com/chart/?symbol={config.TRADINGVIEW_SYMBOL}"

    urgent_html = ""
    if urgent_reasons:
        urgent_html = ("<div class='card' style='border:2px solid #b91c1c;background:#fef2f2;margin-top:10px'>"
                       f"<b class='warn'>{box_title}</b><ul>" + "".join(f"<li>{r}</li>" for r in urgent_reasons) +
                       "</ul></div>")

    rows = ""
    for tf in config.TIMEFRAMES:
        x = t[tf]
        pos = "เหนือ" if x["close"] > x["ema50"] else "ใต้"
        rows += (f"<tr><td><b>{tf}</b> <span class='muted'>{TF_TH[tf]}</span></td>"
                 f"<td><span class='chip {x['key']}'>{x['label']}</span></td>"
                 f"<td class='num'>{x['score']:+d}</td><td class='num'>{x['rsi']:.0f}</td>"
                 f"<td>{pos} EMA50</td><td class='num'>{x['atr']:.2f}</td></tr>")

    if p["side"] != "WAIT":
        plan_rows = (f"<tr><td>จุดเข้า</td><td>{e(p['entry_text'])}</td></tr>"
                     f"<tr><td>Stop Loss</td><td><b>{p['sl']:.2f}</b> <span class='muted'>(~{pts(p['sl'] - p['entry'])} points)</span></td></tr>"
                     f"<tr><td>Take Profit</td><td><b>{p['tp1']:.2f}</b> → <b>{p['tp2']:.2f}</b> "
                     f"<span class='muted'>({config.TP_POINTS[0]}–{config.TP_POINTS[1]} points · R:R ≈ 1:{p['rr']:.1f})</span></td></tr>")
    else:
        plan_rows = f"<tr><td>แนวทาง</td><td>{e(p['entry_text'])}</td></tr>"

    piv = a["pivots"]
    lv = "".join(f"<tr><td class='arrow-dn'>แนวต้าน</td><td class='num'>{x:,.2f}</td><td class='num muted'>+{x - a['price']:.2f}</td></tr>"
                 for x in reversed(a["resistance"][:2]))
    lv += f"<tr><td><b>ราคาปัจจุบัน</b></td><td class='num'><b>{a['price']:,.2f}</b></td><td></td></tr>"
    lv += "".join(f"<tr><td class='arrow-up'>แนวรับ</td><td class='num'>{x:,.2f}</td><td class='num muted'>{x - a['price']:.2f}</td></tr>"
                  for x in a["support"][:2])
    ks = ["R2", "R1", "P", "S1", "S2", "PDH", "PDL"]
    pv = ("<tr>" + "".join(f"<th class='num'>{k}</th>" for k in ks) + "</tr><tr>" +
          "".join(f"<td class='num'>{piv[k]:,.2f}</td>" for k in ks) + "</tr>")

    im = ""
    for name, nm in [("DXY", "ดอลลาร์ DXY"), ("US10Y", "บอนด์ US 10Y (%)")]:
        x = (inter or {}).get(name)
        if x:
            eff = ("กดดันทอง" if x["chg_24h"] > 0 else "หนุนทอง")
            im += (f"<tr><td>{nm}</td><td class='num'>{x['last']:.2f}</td><td class='num'>{sgn(x['chg_1h'], 3)}</td>"
                   f"<td class='num'>{sgn(x['chg_24h'], 3)}</td><td>{eff}</td></tr>")
        else:
            im += f"<tr><td>{nm}</td><td colspan='4' class='muted'>ดึงข้อมูลไม่ได้รอบนี้</td></tr>"

    news_rows = ""
    for i, h in enumerate(headlines[:10]):
        arrow = ("<span class='arrow-up'>▲</span>" if h["score"] > 0 else
                 "<span class='arrow-dn'>▼</span>" if h["score"] < 0 else "<span class='arrow-0'>●</span>")
        th = f"<div>{e(th_heads[i])}</div>" if i < len(th_heads) else ""
        when = tdt(h["time"], with_day=False) if h["time"] else ""
        eff = ("หนุนทอง" if h["score"] > 0 else "กดดันทอง" if h["score"] < 0 else "ผสม")
        why = ""
        if h.get("reasons"):
            why = (f"<div class='why'><b>{eff} · ข่าว{h['strength']}</b> — {e(' / '.join(h['reasons']))}</div>")
        news_rows += (f"<tr><td>{arrow}</td><td>{th}<a href='{e(h['link'])}' class='{'muted' if th else ''}'>{e(h['title'])}</a>{why}</td>"
                      f"<td class='muted' style='white-space:nowrap'>{e(h['source'])}<br>{when}</td></tr>")
    if not news_rows:
        news_rows = "<tr><td colspan='3' class='muted'>ดึงข่าวไม่ได้รอบนี้</td></tr>"

    ev_rows = ""
    for x in events[:10]:
        g = x["guide"]
        when = f"<b>{tdt(x['time'])}</b>"
        if x["time"] <= now:
            r = x.get("reaction")
            res = (f"<span class='chip side'>ออกแล้ว</span> ทอง {sgn(r['first'])} ใน 15 นาทีแรก · "
                   f"{sgn(r['since'])} ถึงตอนนี้ — {r['verdict']}") if r else "<span class='chip side'>ออกแล้ว</span>"
        else:
            res = scenario_text(x)
        ev_rows += (f"<tr><td style='white-space:nowrap'>{when}</td>"
                    f"<td><b>{e(g['name_th'])}</b><div class='muted'>{e(x['title'])}</div></td>"
                    f"<td style='white-space:nowrap'><span class='stars s{g['stars']}'>{g['star_txt']}</span>"
                    f"<div class='muted'>{g['strength']} · สวิง {g['swing']}</div></td>"
                    f"<td>{res}<div class='why'>{e(g['why'])}</div></td></tr>")
    if not ev_rows:
        ev_rows = "<tr><td colspan='4' class='muted'>ไม่มีข่าว USD ระดับกลาง–แรงในช่วงนี้ (หรือดึงปฏิทินไม่ได้)</td></tr>"

    ch_m15 = candle_chart(a["frames"]["M15"], "M15 - last 24h (entry)", a, bars=96, height=2.7)
    ch_h4 = candle_chart(a["frames"]["H4"], "H4 - big picture (~3 weeks)", a, bars=110, height=2.2, plan=False)

    title = f"{box_title} ทองคำ XAUUSD" if urgent_reasons else "รายงานทองคำ XAUUSD รายชั่วโมง"
    return f"""<!doctype html><html lang="th"><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700;800&display=swap" rel="stylesheet">
<title>{title}</title><style>{CSS}</style></head><body>
<div class="head"><div><h1><span class="gold">●</span> {title}</h1>
<div class="muted">{tdt(now)} น. (เวลา LA — ทุกเวลาในรายงานเป็นเวลา LA) · แหล่งราคา: {e(source)}</div></div>
<div class="muted" style="text-align:right"><a href="{tv}">เปิดกราฟ TradingView ›</a></div></div>
{urgent_html}
<div class="hero">
  <div class="card"><div class="muted">ราคาทองตอนนี้</div><div class="big">{a['price']:,.2f}</div>
    <div>{sgn(a['chg']['1h'])} (1 ชม.) · {sgn(a['chg']['24h'])} (24 ชม.)</div>
    <div class="muted">กรอบวันนี้ {a['day_low']:,.2f} – {a['day_high']:,.2f}</div></div>
  <div class="card"><div class="muted">ภาพรวมเทรนด์ (คะแนน {a['bias']:+.1f} / 5)</div>
    <div style="margin:4px 0"><span class="chip {a['bias_key']}" style="font-size:15pt">{a['bias_label']}</span></div>
    <div class="muted">ข่าว: {e(sent['label']) if sent else '-'}</div></div>
  <div class="card" style="text-align:center"><div class="muted">แผนรอบนี้</div>
    <div class="side-big {p['side']}" style="margin-top:4px">{ {'BUY': 'BUY', 'SELL': 'SELL', 'WAIT': 'รอ'}[p['side']] }</div></div>
</div>

<h2>สรุปง่าย ๆ</h2><ul>{''.join(f'<li>{b}</li>' for b in bullets)}</ul>

<h2>แผนเทรด (สไตล์: ดูเทรนด์ใหญ่ → เข้าสั้น {config.TP_POINTS[0]}–{config.TP_POINTS[1]} points)</h2>
<div class="plan"><table>{plan_rows}<tr><td>เหตุผล</td><td>{e(p['why'])}</td></tr></table></div>

<h2>Top-down เทรนด์แต่ละ Timeframe</h2>
<table><tr><th>TF</th><th>เทรนด์</th><th class="num">คะแนน</th><th class="num">RSI</th><th>ราคา</th><th class="num">ATR</th></tr>{rows}</table>
<div class="muted">คะแนน −5 ถึง +5 จาก: ราคา vs EMA50, EMA20 vs EMA50, EMA50 vs EMA200, MACD, RSI</div>


<div class="pb"></div>
<h2>กราฟ</h2>
<img class="chart" src="{ch_m15}"><img class="chart" src="{ch_h4}">
<div class="grid2">
  <div><h2>แนวรับ–แนวต้าน (H1 swing)</h2><table>{lv}</table></div>
  <div><h2>Pivot รายวัน <span class="muted">(PDH/PDL = high/low เมื่อวาน)</span></h2><table>{pv}</table></div>
</div>

<h2>ปัจจัยตลาด</h2>
<table><tr><th></th><th class="num">ล่าสุด</th><th class="num">1 ชม.</th><th class="num">24 ชม.</th><th>ผลต่อทอง</th></tr>{im}</table>

<div class="pb"></div>
<h2>คู่มือข่าวเศรษฐกิจ USD — ออกแบบไหน ทองขึ้นหรือลง (เวลา LA)</h2>
<table class="news"><tr><th>เวลา LA</th><th>ข่าว</th><th>ความแรง</th><th>ผลต่อทอง</th></tr>{ev_rows}</table>
<div class="muted">หลักจำง่าย: ตัวเลขเศรษฐกิจ/เงินเฟ้อสหรัฐ <b>ดีกว่าคาด</b> → ดอลลาร์แข็ง → ทองลง ·
<b>แย่กว่าคาด</b> → ดอลลาร์อ่อน → ทองขึ้น (ยกเว้นอัตราว่างงาน/ผู้ขอสวัสดิการว่างงาน: สูง = ทองขึ้น) ·
★★★★★ แรงมาก = กราฟอาจวิ่ง $15–40 ใน 1–5 นาที</div>

<h2>ข่าวทองล่าสุด + ทำไมถึงหนุน/กดดันทอง</h2>
<table class="news">{news_rows}</table>
<div class="muted">▲ หนุนทอง · ▼ กดดันทอง · ● เป็นกลาง · ความแรงประเมินจากเนื้อหาหัวข่าว (ข่าวด่วน Fed/สงคราม/ภาษี = แรง)</div>

<div class="foot">รายงานอัตโนมัติเพื่อช่วยวางแผน ไม่ใช่คำแนะนำการลงทุน · ราคาในรายงานอาจต่างจากโบรกเกอร์เล็กน้อย —
ยืนยันบนกราฟ TradingView ก่อนเข้าออเดอร์ทุกครั้ง</div>
</body></html>"""


def html_to_pdf(html_str, out_path):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        try:
            b = pw.chromium.launch()
        except Exception:
            b = pw.chromium.launch(channel="chrome")  # GitHub runner มี Google Chrome ติดตั้งไว้แล้ว
        pg = b.new_page()
        pg.set_content(html_str, wait_until="load", timeout=30000)
        try:
            pg.wait_for_load_state("networkidle", timeout=8000)
            pg.evaluate("document.fonts.ready")
        except Exception:
            pass
        pg.pdf(path=out_path, format="A4", print_background=True, prefer_css_page_size=True)
        b.close()
    return out_path


def email_body(a, sent, events, urgent_reasons=None, box_title="แจ้งเตือนด่วน"):
    """ข้อความสั้นในตัวเมล (อ่านบนมือถือได้ทันที)"""
    p = a["plan"]
    side_th = {"BUY": "BUY (ซื้อตามเทรนด์)", "SELL": "SELL (ขายตามเทรนด์)", "WAIT": "รอ (ยังไม่ชัด)"}[p["side"]]
    color = {"BUY": "#15803d", "SELL": "#b91c1c", "WAIT": "#6b7280"}[p["side"]]
    lines = []
    if urgent_reasons:
        lines.append("<div style='background:#fef2f2;border:2px solid #b91c1c;padding:10px;border-radius:8px'>"
                     f"<b style='color:#b91c1c'>{box_title}</b><ul>" +
                     "".join(f"<li>{r}</li>" for r in urgent_reasons) + "</ul></div>")
    lines.append(f"<p style='font-size:22px;margin:8px 0'><b>{a['price']:,.2f}</b> "
                 f"<span style='color:#6b7280;font-size:14px'>{sgn(a['chg']['1h'])} (1ชม.) · {sgn(a['chg']['24h'])} (24ชม.)</span></p>")
    lines.append(f"<p>ภาพรวม: <b>{a['bias_label']}</b> · แผน: <b style='color:{color}'>{side_th}</b></p>")
    t = a["trends"]
    lines.append("<p>" + " · ".join(f"{tf}: {t[tf]['label']}" for tf in config.TIMEFRAMES) + "</p>")
    if p["side"] != "WAIT":
        lines.append(f"<p>{e(p['entry_text'])}<br>SL {p['sl']:.2f} · TP {p['tp1']:.2f} → {p['tp2']:.2f}</p>")
    else:
        lines.append(f"<p>{e(p['entry_text'])}</p>")
    if sent:
        lines.append(f"<p>ข่าว: {e(sent['label'])}</p>")
    now = datetime.now(timezone.utc)
    nb = news_bullets(events)
    if nb:
        lines.append("<ul>" + "".join(f"<li>{b}</li>" for b in nb) + "</ul>")
    nxt = [x for x in events if x["impact"] == "High" and x["time"] > now][:3]
    if nxt:
        lines.append("<p>ข่าวแรงถัดไป (เวลา LA): " + "; ".join(
            f"{tdt(x['time'])} {e(x['guide']['name_th'])} {x['guide']['star_txt']}" for x in nxt) + "</p>")
    lines.append(f"<p><a href='https://www.tradingview.com/chart/?symbol={config.TRADINGVIEW_SYMBOL}'>เปิดกราฟ TradingView</a>"
                 " · รายละเอียดเต็มใน PDF แนบ</p>")
    style = ("<style>.arrow-up{color:#15803d;font-weight:700}.arrow-dn{color:#b91c1c;font-weight:700}"
             ".warn{color:#b91c1c;font-weight:700}</style>")
    return style + "<div style='font-family:Sarabun,Tahoma,sans-serif;font-size:15px;color:#1f2937'>" + "".join(lines) + "</div>"
