"""Gold Bot — รายงานทองรายชั่วโมง + แจ้งเตือนด่วน ส่งเป็น PDF ทางอีเมล

ใช้งาน:
  python main.py report            # รายงานรายชั่วโมง (PDF + อีเมล)
  python main.py alert             # เช็คข่าวแรง/ราคาวิ่งแรง ส่งเมลด่วนเมื่อเจอ
  python main.py weekly            # สรุปประจำสัปดาห์ (วันอาทิตย์ก่อนเที่ยง LA)
  เพิ่ม --dry-run  = สร้าง PDF อย่างเดียว ไม่ส่งเมล
  เพิ่ม --demo     = ใช้ข้อมูลจำลอง (ทดสอบ)
  เพิ่ม --force    = ส่งแม้ตลาดปิด / อยู่ในช่วงงดส่ง
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import ai_summary, analysis, config, mailer, market, news, news_guide, report, weekly


def market_open(now):
    ny = now.astimezone(config.TZ_NY)
    wd, h = ny.weekday(), ny.hour
    if wd == 5 or (wd == 4 and h >= 17) or (wd == 6 and h < 18):
        return False
    return h != 17  # พักตลาดวันละ 1 ชม. (17:00–18:00 NY)


def in_quiet_hours(now):
    if not config.QUIET_HOURS:
        return False
    a, b = (int(x) for x in config.QUIET_HOURS.split("-"))
    h = now.astimezone(config.TZ_LOCAL).hour
    return (a <= h or h < b) if a > b else (a <= h < b)


def load_state():
    try:
        with open(config.STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {"alerted": {}}


def save_state(st):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=4)).isoformat()
    st["alerted"] = {k: v for k, v in st.get("alerted", {}).items() if v > cutoff}
    os.makedirs(os.path.dirname(config.STATE_FILE) or ".", exist_ok=True)
    with open(config.STATE_FILE, "w") as f:
        json.dump(st, f, indent=1)


def gather(demo):
    if demo:
        import demo as D
        frames, source = D.frames()
        inter, heads, cal = D.intermarket(), news.rank_headlines(D.headlines()), D.calendar()
    else:
        frames, source = market.gold_frames()
        inter = market.intermarket()
        heads = news.fetch_headlines()
        cal = news.fetch_calendar() or []
    a = analysis.analyze(frames)
    sent = news.news_sentiment(heads)
    events = news.upcoming(cal)
    for ev in events:  # ข่าวที่ออกไปแล้ว: ดูว่าทองตอบสนองยังไง
        if ev["time"] <= datetime.now(timezone.utc):
            ev["reaction"] = news_guide.reaction(ev, a["frames"]["M15"], a["atr_m15"])
    # ข่าวแรงใกล้ออก (30 นาทีก่อน – 15 นาทีหลัง) → เปลี่ยนแผนเป็น "รอ"
    now = datetime.now(timezone.utc)
    risky = [x for x in events if x["impact"] == "High"
             and -timedelta(minutes=15) <= x["time"] - now <= timedelta(minutes=30)]
    p = a["plan"]
    if risky and p["side"] != "WAIT":
        x = risky[0]
        p.update(side="WAIT", sl=None, tp1=None, tp2=None,
                 entry_text=f"งดเปิดออเดอร์ใหม่ช่วงข่าว {x['title']} ({report.tdt(x['time'], with_day=False)} LA) "
                            f"— กลับมาดูหลังข่าวออก 15 นาที · ทิศทางตามเทรนด์เดิม: {p['side']}",
                 why="ช่วงข่าวแรงกราฟสวิงทั้งสองทาง สเปรดกว้าง SL โดนง่าย")
    return a, source, inter, heads, sent, events


def make_and_send(a, source, inter, heads, sent, events, args, urgent=None, label="ด่วน"):
    ai = ai_summary.summarize(a, heads, events)
    box = "แจ้งเตือนด่วน" if label == "ด่วน" else "สัญญาณเทรด"
    html = report.build_html(a, heads, sent, events, inter, source, ai, urgent, box_title=box)
    os.makedirs("out", exist_ok=True)
    stamp = datetime.now(config.TZ_LOCAL).strftime("%Y%m%d-%H%M")
    pdf = report.html_to_pdf(html, f"out/gold-{'urgent' if urgent else 'report'}-{stamp}.pdf")
    with open("out/last.html", "w") as f:
        f.write(html)
    print("PDF:", pdf)
    side = {"BUY": "BUY", "SELL": "SELL", "WAIT": "รอ"}[a["plan"]["side"]]
    now_l = datetime.now(config.TZ_LOCAL)
    if urgent:
        first = re.sub(r"<[^>]+>", "", urgent[0]).split(" — ")[0].replace("★", "").replace("☆", "")
        first = re.sub(r"\s+", " ", first).strip()
        subject = f"[{label}] ทอง {a['price']:,.2f} — {first[:70]}"
    else:
        subject = f"ทอง {a['price']:,.2f} ({a['chg']['1h']:+.2f}) · {a['bias_label']} · แผน {side} · {now_l:%H:%M}"
    if args.dry_run:
        print("[dry-run] ไม่ส่งเมล | หัวข้อ:", subject)
        return
    box = "แจ้งเตือนด่วน" if label == "ด่วน" else "สัญญาณเทรด"
    mailer.send(subject, report.email_body(a, sent, events, urgent, box_title=box), [pdf])


def cmd_report(args):
    now = datetime.now(timezone.utc)
    if not args.force and not args.demo:
        if not market_open(now):
            print("ตลาดทองปิด — ไม่ส่งรายงาน")
            return
        if in_quiet_hours(now):
            print("อยู่ในช่วงงดส่ง (QUIET_HOURS)")
            return
    make_and_send(*gather(args.demo), args)


SIDE_TH = {"BUY": "BUY", "SELL": "SELL", "WAIT": "รอ"}


def check_signals(a, st):
    """สัญญาณเหมือน TradingView: แผนเปลี่ยน + ราคาตัด EMA20 ตามเทรนด์ใหญ่ (แท่ง M15 ที่ปิดแล้ว)"""
    out = []
    m = a["frames"]["M15"]
    if len(m) < 3:
        return out
    bar, prev = m.iloc[-2], m.iloc[-3]          # แท่งล่าสุดที่ปิดแล้ว / แท่งก่อนหน้า
    t_close = m.index[-2] + timedelta(minutes=15)
    stamp = m.index[-2].strftime("%Y%m%d%H%M")
    p = a["plan"]
    side = p["side"]
    last = st.get("last_side")
    if last and side != last:
        out.append((f"แผนเปลี่ยน: <b>{SIDE_TH.get(last, last)} → {SIDE_TH[side]}</b> · ภาพรวม {a['bias_label']} "
                    f"· ราคา {a['price']:,.2f}" + (f" · {report.e(p['entry_text'])}" if side != "WAIT" else ""),
                    f"sd-{stamp}-{side}"))
    st["last_side"] = side

    sld = p.get("sl_dist") or 0
    tp1 = config.TP_POINTS[0] * config.POINT_VALUE
    tp2 = config.TP_POINTS[1] * config.POINT_VALUE
    c = float(bar["close"])
    when = report.tdt(t_close.to_pydatetime(), with_day=False)
    if side == "BUY" and prev["close"] <= prev["ema20"] and c > bar["ema20"] and c > bar["ema50"]:
        out.append((f"สัญญาณ <b>BUY</b> ตามเทรนด์ — แท่ง M15 ปิด {when} LA ยืนเหนือ EMA20 "
                    f"· เข้า ~{c:,.2f} · SL {c - sld:,.2f} · TP {c + tp1:,.2f} / {c + tp2:,.2f}", f"sg-{stamp}-BUY"))
    if side == "SELL" and prev["close"] >= prev["ema20"] and c < bar["ema20"] and c < bar["ema50"]:
        out.append((f"สัญญาณ <b>SELL</b> ตามเทรนด์ — แท่ง M15 ปิด {when} LA หลุดใต้ EMA20 "
                    f"· เข้า ~{c:,.2f} · SL {c + sld:,.2f} · TP {c - tp1:,.2f} / {c - tp2:,.2f}", f"sg-{stamp}-SELL"))
    return out


def cmd_alert(args):
    now = datetime.now(timezone.utc)
    if not args.force and not args.demo and not market_open(now):
        print("ตลาดปิด — ข้ามการเช็คด่วน")
        return
    a, source, inter, heads, sent, events = gather(args.demo)
    st = load_state()
    done = st.setdefault("alerted", {})
    reasons, keys = [], []

    lead = timedelta(minutes=config.URGENT_EVENT_LEAD_MIN)
    for ev in events:
        k = "ev-" + ev["id"]
        g = ev["guide"]
        if ev["impact"] == "High" and now <= ev["time"] <= now + lead and k not in done:
            mins = int((ev["time"] - now).total_seconds() // 60)
            reasons.append(f"ข่าว{g['strength']} {g['star_txt']} <b>{report.e(g['name_th'])}</b> ออกในอีก ~{mins} นาที "
                           f"({report.tdt(ev['time'], with_day=False)} LA) — {news_guide.scenario_text(ev)} "
                           f"· ทองอาจสวิง {g['swing']} · ปิด/กันกำไรออเดอร์เดิม งดเปิดใหม่")
            keys.append(k)
        r = ev.get("reaction")
        k2 = "rx-" + ev["id"]
        if r and r["big"] and ev["impact"] == "High" and now - ev["time"] <= timedelta(minutes=60) and k2 not in done:
            reasons.append(f"ข่าว <b>{report.e(g['name_th'])}</b> ออกแล้ว — ทอง {r['first']:+.2f} ใน 15 นาทีแรก "
                           f"({r['since']:+.2f} ถึงตอนนี้) · {r['verdict']}")
            keys.append(k2)

    for h in heads:
        k = "nw-" + h["id"]
        if h["urgent"] and h["time"] and now - h["time"] <= timedelta(minutes=45) and k not in done:
            eff = "หนุนทอง ▲" if h["score"] > 0 else "กดดันทอง ▼" if h["score"] < 0 else "จับตา"
            why = (" — " + report.e(" / ".join(h["reasons"]))) if h.get("reasons") else ""
            reasons.append(f"ข่าวด่วน ({eff}, ข่าว{h['strength']}): <b>{report.e(h['title'])}</b> "
                           f"({report.e(h['source'])}, {report.tdt(h['time'], with_day=False)} LA){why}")
            keys.append(k)

    rng, atr_h1 = a["last_h1_range"], a["atr_h1"]
    k = "mv-" + now.strftime("%Y%m%d%H")
    if atr_h1 > 0 and rng > config.URGENT_MOVE_ATR * atr_h1 and k not in done:
        reasons.append(f"ราคาวิ่งแรง: แท่ง H1 นี้กว้าง {rng:.2f} (≈{rng / atr_h1:.1f} เท่าของ ATR {atr_h1:.2f})")
        keys.append(k)

    sig_reasons, sig_keys = [], []
    for txt, k in check_signals(a, st):
        if k not in done:
            sig_reasons.append(txt)
            sig_keys.append(k)

    if not reasons and not sig_reasons:
        print("ไม่มีเหตุด่วน / ไม่มีสัญญาณ")
        save_state(st)
        return
    label = "ด่วน" if reasons else "สัญญาณ"
    allr = sig_reasons + reasons
    print(label + ":", *allr, sep="\n - ")
    make_and_send(a, source, inter, heads, sent, events, args, urgent=allr[:6], label=label)
    for k in keys + sig_keys:
        done[k] = now.isoformat()
    save_state(st)


def cmd_weekly(args):
    """สรุปประจำสัปดาห์ — ส่งวันอาทิตย์ก่อนเที่ยง LA"""
    if args.demo:
        import demo as D
        frames, source = D.frames()
        inter, heads, cal = D.intermarket(), news.rank_headlines(D.headlines(), 72), D.week_calendar()
    else:
        frames, source = market.gold_frames()
        inter = market.intermarket()
        heads = news.fetch_headlines(hours=72, limit=15)
        cal = news.fetch_calendar(next_week=True) or []
    w = weekly.analyze_week(frames)
    events = weekly.week_events(cal)
    sent = news.news_sentiment(heads)
    ai = ai_summary.summarize_week(w, heads, events)
    html = weekly.build_weekly_html(w, events, heads, sent, inter, source, ai)
    os.makedirs("out", exist_ok=True)
    stamp = datetime.now(config.TZ_LOCAL).strftime("%Y%m%d")
    pdf = report.html_to_pdf(html, f"out/gold-weekly-{stamp}.pdf")
    print("PDF:", pdf)
    side = {"BUY": "เน้น BUY", "SELL": "เน้น SELL", "WAIT": "เทรดในกรอบ"}[w["side"]]
    nbig = sum(1 for x in events if x["guide"]["stars"] >= 4)
    subject = f"สรุปทองประจำสัปดาห์ · {w['bias_label']} · {side} · ข่าวแรง {nbig} ข่าว"
    if args.dry_run:
        print("[dry-run] ไม่ส่งเมล | หัวข้อ:", subject)
        return
    mailer.send(subject, weekly.weekly_email(w, events), [pdf])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["report", "alert", "weekly"])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    try:
        {"report": cmd_report, "alert": cmd_alert, "weekly": cmd_weekly}[args.mode](args)
    except Exception as ex:
        print("ERROR:", ex)
        raise
    sys.exit(0)
