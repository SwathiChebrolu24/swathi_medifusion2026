
import smtplib
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv

load_dotenv()

smtp_server = os.getenv("SMTP_SERVER")
smtp_port = os.getenv("SMTP_PORT")
sender_email = os.getenv("SMTP_USERNAME")
sender_password = os.getenv("SMTP_PASSWORD")

print("-" * 50)
print(f"📧 Testing SMTP Configuration for: {sender_email}")
print(f"🌐 Server: {smtp_server}:{smtp_port}")
print("-" * 50)

try:
    print("Attempting to connect...")
    server = smtplib.SMTP(smtp_server, int(smtp_port))
    server.starttls()
    print("✅ Connected and TLS started.")
    
    print("Attempting to login...")
    server.login(sender_email, sender_password)
    print("✅ LOGIN SUCCESSFUL!")
    
    # Send a test email to self
    msg = MIMEText("This is a test email from MediFusion setup.")
    msg['Subject'] = "MediFusion SMTP Test"
    msg['From'] = sender_email
    msg['To'] = sender_email
    
    print("Attempting to send test email to self...")
    server.sendmail(sender_email, sender_email, msg.as_string())
    print("✅ TEST EMAIL SENT SUCCESSFULLY!")
    
    server.quit()
    print("-" * 50)
    print("🎉 configuration is VALID. You are ready to go!")
    
except Exception as e:
    print("\n❌ ERROR: Connection Failed")
    print(f"Details: {e}")
    print("\nCommon fixes:")
    print("1. Check if 'Less Secure Apps' is ON or if using App Password.")
    print("2. Verify there are no spaces in your password in .env")
    print("3. Check internet connection.")
