import random

otp_store = {}

def generate_otp():
    return str(random.randint(100000, 999999))

def verify_otp(email: str, otp: str):
    return otp_store.get(email) == otp
