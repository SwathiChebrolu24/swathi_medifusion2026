import sys
import bcrypt
from passlib.context import CryptContext

print(f"Python version: {sys.version}")
print(f"Bcrypt version: {bcrypt.__version__}")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

password = "password123"
print(f"Password: {password}")
print(f"Length: {len(password)}")

try:
    print("Attempting hash with passlib...")
    hashed = pwd_context.hash(password)
    print(f"Success! Hash: {hashed}")
except Exception as e:
    print(f"Passlib Error: {e}")
    import traceback
    traceback.print_exc()

try:
    print("Attempting hash with bcrypt directly...")
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    print(f"Success! Hash: {hashed}")
except Exception as e:
    print(f"Bcrypt Error: {e}")
    import traceback
    traceback.print_exc()
