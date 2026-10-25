"""ตั้งค่าทั้งหมดของโปรแกรม — อ่านจาก Environment variables (GitHub Secrets)"""
import os
from zoneinfo import ZoneInfo


def _env(name, default=""):
    v = os.environ.get(name, "")
    return v.strip() if v and v.strip() else default


# ---------- อีเมล ----------
GMAIL_USER = _env("GMAIL_USER")                      # Gmail ที่ใช้ส่ง
GMAIL_APP_PASSWORD = _env("GMAIL_APP_PASSWORD")      # App Password 16 ตัว
MAIL_TO = _env("MAIL_TO", "Thaiger.bites333@gmail.com")  # คั่นหลายเมลด้วย ,

# ---------- แหล่งข้อมูล ----------
# ถ้ามีคีย์ Twelve Data (ฟรี) จะใช้ราคา Spot XAU/USD ใกล้เคียง TradingView (OANDA:XAUUSD)
# ถ้าไม่มี จะใช้ Yahoo Finance GC=F (ทองฟิวเจอร์ส COMEX — ราคาสูงกว่า spot เล็กน้อย)
TWELVEDATA_API_KEY = _env("TWELVEDATA_API_KEY")
ANTHROPIC_API_KEY = _env("ANTHROPIC_API_KEY")        # (ไม่บังคับ) ให้ Claude สรุปข่าวเป็นภาษาไทย
CLAUDE_MODEL = _env("CLAUDE_MODEL", "claude-sonnet-4-5")

# ---------- การเทรด ----------
POINT_VALUE = float(_env("POINT_VALUE", "0.01"))     # 1 point = $0.01 (XAUUSD 2 ทศนิยม)
TP_POINTS = (int(_env("TP_MIN_POINTS", "200")), int(_env("TP_MAX_POINTS", "300")))
TRADINGVIEW_SYMBOL = _env("TRADINGVIEW_SYMBOL", "OANDA:XAUUSD")

# ---------- เวลา ----------
TZ_LOCAL = ZoneInfo("America/Los_Angeles")   # ทุกเวลาในรายงาน/อีเมล = เวลา LA
TZ_NY = ZoneInfo("America/New_York")
# ช่วงงดส่งรายงานรายชั่วโมง (เวลาท้องถิ่น) เช่น "23-5" = งด 23:00–04:59 ; ว่าง = ส่งตลอด
QUIET_HOURS = _env("QUIET_HOURS", "")

# ---------- แจ้งเตือนด่วน ----------
URGENT_EVENT_LEAD_MIN = int(_env("URGENT_EVENT_LEAD_MIN", "45"))  # เตือนก่อนข่าวแรงกี่นาที
URGENT_MOVE_ATR = float(_env("URGENT_MOVE_ATR", "1.5"))          # แท่ง H1 วิ่งเกิน x เท่า ATR = ด่วน
STATE_FILE = _env("STATE_FILE", "state/state.json")

TIMEFRAMES = ["D1", "H4", "H1", "M30", "M15"]
TF_WEIGHT = {"D1": 0.30, "H4": 0.25, "H1": 0.20, "M30": 0.15, "M15": 0.10}
