import os
import sys
from dotenv import load_dotenv

# Add the backend directory to sys.path to allow importing app modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

load_dotenv(os.path.join(os.path.dirname(__file__), 'backend', '.env'))

from app.core.email import send_otp_email

if __name__ == "__main__":
    email = input("Enter an email address to send a test OTP to: ")
    print(f"Sending test OTP to {email}...")
    send_otp_email(email, "123456")
    print("Done. Check usage logs above for success/failure.")
