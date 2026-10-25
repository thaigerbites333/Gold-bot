"""(ไม่บังคับ) ให้ Claude สรุปข่าว + เทรนด์เป็นภาษาไทยง่าย ๆ — ใช้เมื่อมี ANTHROPIC_API_KEY"""
import json
import requests

from . import config


def summarize(a, headlines, events):
    if not config.ANTHROPIC_API_KEY:
        return None
    t = a["trends"]
    ctx = {
        "price": round(a["price"], 2), "change_1h": round(a["chg"]["1h"], 2), "change_24h": round(a["chg"]["24h"], 2),
        "trend": {tf: t[tf]["label"] for tf in t}, "bias": a["bias_label"], "plan": a["plan"]["side"],
        "support": a["support"], "resistance": a["resistance"],
        "headlines": [h["title"] for h in headlines[:10]],
        "events_LA_time": [f'{e["time"].astimezone(config.TZ_LOCAL):%a %H:%M} LA {e["title"]} ({e["impact"]}, '
                           f'forecast {e.get("forecast")}, previous {e.get("previous")})' for e in events[:6]],
    }
    prompt = (
        "คุณเป็นผู้ช่วยนักเทรดทองคำ (XAUUSD) ที่เทรดสั้น 15–30 นาที ตามเทรนด์ใหญ่\n"
        "สรุปสถานการณ์จากข้อมูลนี้เป็นภาษาไทยง่าย ๆ ตอบเป็น JSON เท่านั้น รูปแบบ:\n"
        '{"summary": ["bullet 3-5 ข้อ สั้น ๆ"], "headlines_th": ["แปลหัวข่าวเป็นไทยสั้น ๆ ตามลำดับเดิม"], '
        '"watch": "สิ่งที่ต้องระวังที่สุดใน 1-2 ชม.ข้างหน้า 1 ประโยค"}\n'
        "ใน summary ให้มีอย่างน้อย 1 ข้อที่อธิบายข่าวสำคัญ: ข่าวแรงแค่ไหน และถ้าออกมาดี/แย่กว่าคาดทองจะขึ้นหรือลงเพราะอะไร\n"
        "เวลาทั้งหมดใช้เวลา LA\n"
        "ห้ามแนะนำให้ลงเงินเกินตัว ไม่ต้องใส่คำเตือนยาว ๆ\n\nข้อมูล:\n" + json.dumps(ctx, ensure_ascii=False)
    )
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": config.ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": config.CLAUDE_MODEL, "max_tokens": 1200,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=60,
        )
        r.raise_for_status()
        text = "".join(b.get("text", "") for b in r.json()["content"])
        text = text[text.find("{"): text.rfind("}") + 1]
        return json.loads(text)
    except Exception as e:
        print("[warn] Claude summary:", e)
        return None


def summarize_week(w, headlines, events):
    """(ไม่บังคับ) สรุปภาพรวมสัปดาห์หน้าเป็นภาษาไทย"""
    if not config.ANTHROPIC_API_KEY:
        return None
    ctx = {
        "last_week": {k: round(v, 2) for k, v in w["recap"].items()},
        "trend": {k: v["label"] for k, v in w["trends"].items()}, "bias": w["bias_label"], "plan": w["side"],
        "weekly_pivots": {k: round(v, 2) for k, v in w["pivots"].items()},
        "headlines_last_3_days": [h["title"] for h in headlines[:12]],
        "events_this_week_LA": [f'{e["time"].astimezone(config.TZ_LOCAL):%a %H:%M} {e["title"]} ({e["impact"]}, '
                                f'forecast {e.get("forecast")})' for e in events[:20]],
    }
    prompt = (
        "คุณเป็นผู้ช่วยนักเทรดทองคำ (XAUUSD) สรุปภาพรวมสัปดาห์หน้าเป็นภาษาไทยง่าย ๆ "
        "ตอบเป็น JSON เท่านั้น: {\"summary\": [\"bullet 4-6 ข้อ\"]} "
        "ต้องมี: เทรนด์ใหญ่, ข่าวที่สำคัญที่สุดของสัปดาห์และถ้าออกมาดี/แย่กว่าคาดทองจะขึ้นหรือลงเพราะอะไร, "
        "วันที่ต้องระวัง, ธีมข่าวที่ตลาดสนใจ · เวลาใช้เวลา LA\n\nข้อมูล:\n" + json.dumps(ctx, ensure_ascii=False))
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": config.ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": config.CLAUDE_MODEL, "max_tokens": 1200, "messages": [{"role": "user", "content": prompt}]},
            timeout=60)
        r.raise_for_status()
        text = "".join(b.get("text", "") for b in r.json()["content"])
        return json.loads(text[text.find("{"): text.rfind("}") + 1])
    except Exception as e:
        print("[warn] Claude weekly summary:", e)
        return None
