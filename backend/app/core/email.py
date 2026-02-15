import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import logging

logger = logging.getLogger(__name__)

def send_otp_email(to_email: str, otp: str):
    """
    Sends an OTP email using SMTP settings from environment variables.
    """
    sender_email = os.getenv("SMTP_USERNAME")
    sender_password = os.getenv("SMTP_PASSWORD")
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))

    if not sender_email or not sender_password:
        logger.warning("⚠️ SMTP credentials missing in .env. OTP email NOT sent.")
        return

    msg = MIMEMultipart()
    msg['From'] = f"MediFusion <{sender_email}>"
    msg['To'] = to_email
    msg['Subject'] = "MediFusion Verification Code"

    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                <h2 style="color: #00d4aa; text-align: center;">MediFusion</h2>
                <p>Hello,</p>
                <p>Your verification code for MediFusion is:</p>
                <div style="background-color: #f4f6f8; padding: 15px; text-align: center; border-radius: 5px; font-size: 24px; font-weight: bold; letter-spacing: 5px; color: #0a0e27;">
                    {otp}
                </div>
                <p style="margin-top: 20px;">Use this code to complete your signup. This code will expire in 10 minutes.</p>
                <p style="font-size: 12px; color: #888; text-align: center; margin-top: 30px;">
                    &copy; 2026 MediFusion. All rights reserved.
                </p>
            </div>
        </body>
    </html>
    """

    msg.attach(MIMEText(html_body, 'html'))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, to_email, text)
        server.quit()
        logger.info(f"✅ Email sent successfully to {to_email}")
    except Exception as e:
        logger.error(f"❌ Failed to send email to {to_email}: {e}")
