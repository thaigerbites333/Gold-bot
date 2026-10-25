"""ส่งอีเมลผ่าน Gmail (ใช้ App Password)"""
import os
import smtplib
from email.message import EmailMessage

from . import config


def send(subject, html_body, attachments=()):
    if not (config.GMAIL_USER and config.GMAIL_APP_PASSWORD):
        raise RuntimeError("ยังไม่ได้ตั้ง GMAIL_USER / GMAIL_APP_PASSWORD")
    to = [x.strip() for x in config.MAIL_TO.split(",") if x.strip()]
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"Gold Bot <{config.GMAIL_USER}>"
    msg["To"] = ", ".join(to)
    msg.set_content("เปิดอีเมลนี้ในแอปที่รองรับ HTML หรือดู PDF ที่แนบมา")
    msg.add_alternative(html_body, subtype="html")
    for path in attachments:
        with open(path, "rb") as f:
            msg.add_attachment(f.read(), maintype="application", subtype="pdf", filename=os.path.basename(path))
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as s:
        s.starttls()
        s.login(config.GMAIL_USER, config.GMAIL_APP_PASSWORD)
        s.send_message(msg)
    print("ส่งอีเมลแล้ว ->", msg["To"])
