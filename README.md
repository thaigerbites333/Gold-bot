# Gold Bot — รายงานทองรายชั่วโมง + แจ้งเตือนด่วน (PDF ทางอีเมล)

โปรแกรมจะทำงานเองบน **GitHub Actions (ฟรี)** ไม่ต้องเปิดคอมทิ้งไว้ · **ทุกเวลาในรายงานและอีเมลเป็นเวลา LA**

| ทำอะไร | เมื่อไหร่ |
|---|---|
| รายงาน PDF: ราคา, เทรนด์ D1→H4→H1→M30→M15, แผน BUY/SELL/รอ + SL/TP, แนวรับ-ต้าน, Pivot, กราฟ, DXY/US10Y, ปฏิทินข่าว USD, ข่าวทองล่าสุด | ทุกชั่วโมง (ช่วงตลาดเปิด) |
| อีเมล **[ด่วน]** + PDF | ข่าว USD แรง (High) จะออกในอีก ≤45 นาที · ข่าวด่วน (Fed/สงคราม/ภาษี ฯลฯ) · แท่ง H1 วิ่งเกิน 1.5 เท่า ATR |
| คู่มือข่าว: ข่าวนี้แรงแค่ไหน (★1–5), ออกมาสูง/ต่ำกว่าคาดแล้วทองขึ้นหรือลง เพราะอะไร, ข่าวที่ออกแล้วทองตอบสนองยังไง, หัวข่าวแต่ละข่าวหนุน/กดดันทองเพราะอะไร | ทุกรายงาน + อีเมลด่วน |
| **สรุปประจำสัปดาห์** (PDF): ทองสัปดาห์ที่แล้ว, เทรนด์ใหญ่ W1/D1/H4 → มุมมองสัปดาห์หน้า, แผน BUY/SELL/เทรดในกรอบ, ฉากทัศน์ขึ้น/ลง, แนวรับ-ต้าน + Pivot รายสัปดาห์, กรอบที่คาดว่าจะวิ่ง, ปฏิทินข่าว USD ทั้งสัปดาห์แยกรายวัน (★ความแรง + ออกแบบไหนทองขึ้น/ลง), วันที่ต้องระวังที่สุด, ธีมข่าว | **ทุกวันอาทิตย์ 09:47 LA** (หลังเปลี่ยนเวลาหน้าหนาว = 08:47) (ก่อนตลาดเปิด 15:00 LA) |
| แผนเปลี่ยนเป็น "รอ" อัตโนมัติ | 30 นาทีก่อน – 15 นาทีหลังข่าวแรง |
| Indicator บน TradingView | ตาราง Top-down + สัญญาณ BUY/SELL + Alert บนกราฟจริง |

---

## ติดตั้ง (ครั้งเดียว ~15 นาที)

### 1) สร้าง Gmail App Password
1. เข้า https://myaccount.google.com/security → เปิด **2-Step Verification**
2. เข้า https://myaccount.google.com/apppasswords → ตั้งชื่อ `Gold Bot` → กด Create
3. จดรหัส 16 ตัวไว้ (ไม่ต้องเว้นวรรค)

### 2) สร้าง GitHub repo
1. สมัคร/ล็อกอิน https://github.com → **New repository** ชื่อ `gold-bot`
2. เลือก **Public** (ใช้นาทีรันฟรีไม่จำกัด — รหัสผ่านเก็บใน Secrets ไม่มีใครเห็น)
   *ถ้าอยากเป็น Private: ฟรี 2,000 นาที/เดือน ไม่พอสำหรับเช็คทุก 15 นาที → แก้ cron บรรทัดที่ 2 ใน `.github/workflows/gold-bot.yml` เป็น `"26,56 * * * 0-5"` (ทุก 30 นาที)*
3. กด **uploading an existing file** → ลากไฟล์ทั้งหมดจาก zip ลงไป (รวมโฟลเดอร์ `.github`) → Commit
   *ถ้าโฟลเดอร์ `.github` ไม่ขึ้น: Add file → Create new file → พิมพ์ชื่อ `.github/workflows/gold-bot.yml` แล้ววางเนื้อหาไฟล์*

### 3) ใส่ Secrets
repo → **Settings → Secrets and variables → Actions → New repository secret**

| ชื่อ | ค่า | จำเป็น? |
|---|---|---|
| `GMAIL_USER` | Gmail ที่ใช้ส่ง เช่น `you@gmail.com` | ✔ |
| `GMAIL_APP_PASSWORD` | รหัส 16 ตัวจากข้อ 1 | ✔ |
| `MAIL_TO` | อีเมลผู้รับ (หลายคนคั่นด้วย `,`) — ไม่ใส่ = `Thaiger.bites333@gmail.com` | |
| `TWELVEDATA_API_KEY` | คีย์ฟรีจาก https://twelvedata.com (ราคา **Spot** ตรงกับ OANDA:XAUUSD) | แนะนำมาก |
| `ANTHROPIC_API_KEY` | ให้ Claude สรุปข่าว + แปลหัวข่าวเป็นภาษาไทย (มีค่าใช้จ่ายเล็กน้อย) | |

> ถ้าไม่มี Twelve Data จะใช้ Yahoo **GC=F** (ทองฟิวเจอร์ส) ซึ่งสูงกว่า Spot ราว $10–40 → แนวรับ/ต้าน/SL/TP จะเลื่อนจากกราฟ TradingView

ตัวเลือกเพิ่ม (แท็บ **Variables**):
- `QUIET_HOURS` = ช่วงงดส่งรายงานรายชั่วโมง (เวลา LA) เช่น `23-5` (แจ้งเตือนด่วนยังส่งตามปกติ)

### 4) ทดสอบ
repo → **Actions** → (ถ้าถามให้กด *I understand… enable*) → **Gold Bot** → **Run workflow** → mode `report`, force `true` → รอ ~2 นาที แล้วเช็คอีเมล
(ทดสอบสรุปรายสัปดาห์: ใส่ mode `weekly`)

หลังจากนั้นจะรันเองทุกชั่วโมง ✔

---

## TradingView (แพ็กเกจฟรีใช้ได้)
1. เปิดกราฟ **OANDA:XAUUSD** (M15 หรือ M30)
2. ล่างจอ **Pine Editor** → ลบโค้ดเดิม → วางโค้ดจาก `tradingview/gold_topdown.pine` → **Save** → **Add to chart**
3. จะเห็น EMA20/50/200, Pivot รายวัน, ตาราง Top-down มุมขวาบน, ป้าย BUY/SELL เมื่อราคาย่อแล้วกลับตัวตามเทรนด์ใหญ่
4. ตั้ง Alert: ⏰ **Alert** → Condition: `Gold Top-down (Kit)` → **Any alert() function call** → Notifications: App / Email → Create
   (แจ้งเมื่อแผนเปลี่ยน BUY/SELL/รอ และเมื่อมีสัญญาณเข้า)

สูตรใน Pine กับรายงาน PDF เป็นสูตรเดียวกัน (คะแนน −5..+5 จาก ราคา vs EMA50, EMA20 vs EMA50, EMA50 vs EMA200, MACD, RSI · น้ำหนัก D1 30%, H4 25%, H1 20%, M30 15%, M15 10%)

---

## ปรับแต่ง (Settings → Secrets and variables → Actions → แท็บ Variables)
| ชื่อ | ค่าเริ่มต้น | ความหมาย |
|---|---|---|
| `TP_MIN_POINTS` / `TP_MAX_POINTS` | 200 / 300 | เป้า TP (1 point = $0.01) |
| `URGENT_EVENT_LEAD_MIN` | 45 | เตือนก่อนข่าวแรงกี่นาที |
| `URGENT_MOVE_ATR` | 1.5 | แท่ง H1 กว้างกี่เท่า ATR ถึงเตือนด่วน |

## รันบนคอมตัวเอง (ทดสอบ)
```bash
pip install -r requirements.txt && python -m playwright install chromium
python main.py report --demo --dry-run   # ข้อมูลจำลอง สร้าง PDF ใน out/
python main.py report --dry-run          # ข้อมูลจริง ไม่ส่งเมล
python main.py weekly --demo --dry-run   # ทดสอบสรุปประจำสัปดาห์
```

## ข้อควรรู้
- GitHub อาจรันช้ากว่าเวลาที่ตั้ง 5–15 นาทีในช่วงคนใช้เยอะ (สรุปรายสัปดาห์ตั้งไว้ 09:47 LA จึงมีเวลาเผื่อก่อนเที่ยงหลายชั่วโมง)
- Repo สาธารณะที่ไม่มีการแก้ไขนาน 60 วัน GitHub จะหยุดตารางเวลา → เข้า Actions กด Enable อีกครั้ง
- แหล่งข่าว: Google News (Reuters, Kitco, World Gold Council, Fed/USD), FXStreet · ปฏิทิน: Forex Factory
- รายงานเพื่อช่วยวางแผนเท่านั้น ไม่ใช่คำแนะนำการลงทุน ยืนยันบนกราฟก่อนเข้าออเดอร์เสมอ
