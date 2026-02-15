# app/api/auth/routes.py
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from typing import Dict, Union
from sqlalchemy.orm import Session
import random

from app.schemas.user_schema import UserCreate, UserOut
from app.models.user import User as UserModel
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Auth"])

# Predefined licenses (generated for testing)
# DOC001 to DOC021
DOCTOR_LICENSES = [f"DOC{str(i).zfill(3)}" for i in range(1, 22)]
# LAB001 to LAB021
LAB_LICENSES = [f"LAB{str(i).zfill(3)}" for i in range(1, 22)]

# -----------------------------
# Helpers
# -----------------------------
def get_user_by_username(db: Session, username: str):
    return db.query(UserModel).filter(UserModel.username == username).first()

def get_user_by_email(db: Session, email: str):
    return db.query(UserModel).filter(UserModel.email == email).first()

# -----------------------------
# Signup
# -----------------------------
@router.post("/signup", response_model=Union[UserOut, Dict])
def signup(user: UserCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Signup for doctor / lab / patient.
    - Doctor & Lab: require license_code (matched against lists)
    - Patient: provide email -> receive OTP (returned in response in testing mode)
    """
    # ---------- doctor ----------
    if user.role == "doctor":
        if not user.license_code or user.license_code not in DOCTOR_LICENSES:
            raise HTTPException(status_code=400, detail="Invalid doctor license")

        if get_user_by_username(db, user.username):
            raise HTTPException(status_code=400, detail="Username already exists")
            
        # Check if license is already in use
        existing_license = db.query(UserModel).filter(UserModel.license_code == user.license_code).first()
        if existing_license:
            raise HTTPException(status_code=400, detail="License code already in use by another user")

        db_user = UserModel(
            username=user.username,
            password=hash_password(user.password),
            full_name=user.full_name,
            role="doctor",
            is_doctor=True,
            is_verified=True,  # doctors are considered verified on signup (license check done)
            license_code=user.license_code  # Store the license code
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        return UserOut(id=db_user.id, username=db_user.username, full_name=db_user.full_name, role=db_user.role)

    # ---------- lab ----------
    if user.role == "lab":
        if not user.license_code or user.license_code not in LAB_LICENSES:
            raise HTTPException(status_code=400, detail="Invalid lab license")

        if get_user_by_username(db, user.username):
            raise HTTPException(status_code=400, detail="Username already exists")
            
        # Check if license is already in use
        existing_license = db.query(UserModel).filter(UserModel.license_code == user.license_code).first()
        if existing_license:
            raise HTTPException(status_code=400, detail="License code already in use by another user")

        db_user = UserModel(
            username=user.username,
            password=hash_password(user.password),
            full_name=user.full_name,
            role="lab",
            is_lab=True,
            is_verified=True,  # labs considered verified on signup (license check done)
            license_code=user.license_code  # Store the license code
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        return UserOut(id=db_user.id, username=db_user.username, full_name=db_user.full_name, role=db_user.role)

    # ---------- patient ----------
    if user.role == "patient":
        if not user.email:
            raise HTTPException(status_code=400, detail="Patient email required for OTP")

        if get_user_by_username(db, user.username):
            raise HTTPException(status_code=400, detail="Username already exists")
        if get_user_by_email(db, user.email):
            raise HTTPException(status_code=400, detail="Email already registered")

        # generate OTP
        otp = str(random.randint(100000, 999999))

        # create user record with OTP and is_verified=False
        db_user = UserModel(
            username=user.username,
            password=hash_password(user.password),
            full_name=user.full_name,
            role="patient",
            email=user.email,
            otp=otp,
            is_verified=False
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        # Send OTP via Email (Background Task)
        from app.core.email import send_otp_email
        background_tasks.add_task(send_otp_email, user.email, otp)

        # Return OTP in response for testing/dev mode
        return {"message": f"OTP sent to {user.email}. Please check your inbox.", "otp_sent": True, "otp": otp}

    raise HTTPException(status_code=400, detail="Invalid role")

# -----------------------------
# Verify OTP and activate account
# -----------------------------
@router.post("/verify-otp", response_model=Dict)
def verify_otp(email: str, otp: str, db: Session = Depends(get_db)):
    """
    Verify OTP (testing) and mark the patient user as verified.
    Only requires email + otp (other details already saved at /signup).
    """
    user = get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=400, detail="Email not registered")

    if user.is_verified:
        return {"message": "User already verified."}

    if not user.otp or user.otp != otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    # mark verified and clear OTP
    user.is_verified = True
    user.otp = None
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"message": "OTP verified. Signup complete.", "user": {"id": user.id, "username": user.username, "full_name": user.full_name, "role": user.role}}

# -----------------------------
# Login (OAuth2 form)
# -----------------------------
@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Login using form data (username + password).
    Returns JWT token and user info. Only verified users can login.
    """
    username = form_data.username
    password = form_data.password

    db_user = get_user_by_username(db, username)
    if not db_user:
        raise HTTPException(status_code=400, detail="Invalid username or password")

    # only allow login if verified (doctors/labs were set verified at signup)
    if not db_user.is_verified:
        raise HTTPException(status_code=403, detail="Account not verified. Please verify OTP before login.")

    if not verify_password(password, db_user.password):
        raise HTTPException(status_code=400, detail="Invalid username or password")

    token = create_access_token({"sub": db_user.username, "role": db_user.role})
    return {"message": "Login successful", "access_token": token, "token_type": "bearer", "user": {"id": db_user.id, "username": db_user.username, "full_name": db_user.full_name, "role": db_user.role}}

# -----------------------------
# Me endpoint (using Authorization header)
# -----------------------------
from fastapi import Header

def get_current_user_from_token(authorization: str = Header(...), db: Session = Depends(get_db)):
    """
    Expect header: Authorization: Bearer <token>
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.split(" ")[1]
    payload = None
    try:
        from app.core.security import decode_access_token
        payload = decode_access_token(token)
    except Exception:
        payload = None

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user

@router.get("/me")
def me(current_user: UserModel = Depends(get_current_user_from_token)):
    return {"id": current_user.id, "username": current_user.username, "full_name": current_user.full_name, "role": current_user.role}

# -----------------------------
# Debug endpoint: view OTP for an email (testing only)
# -----------------------------
@router.get("/debug/otp")
def debug_get_otp(email: str, db: Session = Depends(get_db)):
    user = get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="Email not found")
    return {"email": email, "otp": user.otp, "is_verified": user.is_verified}


from fastapi import Depends
from app.core.role_checker import role_required

@router.get("/doctor/dashboard")
def doctor_dashboard(user = Depends(role_required("doctor"))):
    return {"message": "Welcome Doctor!", "user": user.username}

@router.get("/patient/dashboard")
def patient_dashboard(user = Depends(role_required("patient"))):
    return {"message": "Welcome Patient!", "user": user.username}

@router.get("/lab/dashboard")
def lab_dashboard(user = Depends(role_required("lab"))):
    return {"message": "Welcome Lab!", "user": user.username}
