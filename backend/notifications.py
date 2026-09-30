"""
Simple email notifier using SMTP (Gmail works fine with an App Password).
This is the 'API integration' piece — no external paid API needed, just SMTP.

To enable: set these environment variables (or put them in a .env file):
  MAIL_ENABLED=true
  MAIL_ADDRESS=youremail@gmail.com
  MAIL_APP_PASSWORD=xxxxxxxxxxxxxxxx   (Gmail App Password, not your real password)

If MAIL_ENABLED is not "true", this silently no-ops — so the app still runs
fine without any email setup (useful for quick demos/interviews).
"""

import os
import smtplib
from email.mime.text import MIMEText

MAIL_ENABLED = os.environ.get("MAIL_ENABLED", "false").lower() == "true"
MAIL_ADDRESS = os.environ.get("MAIL_ADDRESS", "")
MAIL_APP_PASSWORD = os.environ.get("MAIL_APP_PASSWORD", "")


def send_match_alert(to_email: str, item_title: str, matched_title: str, similarity: float, matched_image_url: str):
    """Sends a plain-text email alert when a strong match is found. Fails silently on error
    so a broken/missing mail config never breaks the upload flow."""
    if not MAIL_ENABLED or not to_email:
        return False

    try:
        subject = f"Possible match found for your item: {item_title}"
        body = (
            f"Good news! We found a possible match for your report '{item_title}'.\n\n"
            f"Matched item: {matched_title}\n"
            f"Similarity score: {round(similarity * 100)}%\n"
            f"View it here: http://127.0.0.1:5000{matched_image_url}\n\n"
            f"Log in to the Campus Lost & Found portal to confirm and claim it."
        )
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = MAIL_ADDRESS
        msg["To"] = to_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(MAIL_ADDRESS, MAIL_APP_PASSWORD)
            server.sendmail(MAIL_ADDRESS, [to_email], msg.as_string())
        return True
    except Exception as e:
        print(f"[mail] failed to send alert: {e}")
        return False
