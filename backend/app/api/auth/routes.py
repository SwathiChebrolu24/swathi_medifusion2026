# app/api/auth/routes.py
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Header
from fastapi.security import OAuth2PasswordRequestForm
from typing import Dict, Union
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import random
import logging

from app.schemas.user_schema import UserCreate, UserOut
from app.models.user import User as UserModel
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth"])

# Predefined licenses (DOC001–DOC021, LAB001–LAB021)
DOCTOR_LICENSES = [f"DOC{str(i).zfill(3)}" for i in range(1, 22)]
LAB_LICENSES    = [f"LAB{str(i).zfill(3)}" for i in range(1, 22)]

OTP_EXPIRY_MINUTES = 10  # OTP valid for 10 minutes


# --------------------------------------------------
# Helpers
# --------------------------------------------------
def get_user_by_username(db: Session, username: str):
    return db.query(UserModel).filter(UserModel.username == username).first()

def get_user_by_email(db: Session, email: str):
    return db.query(UserModel).filter(UserModel.email == email).first()


# --------------------------------------------------
# Signup
# --------------------------------------------------
@router.post("/signup", response_model=Union[UserOut, Dict])
def signup(user: UserCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Signup for doctor / lab / patient.
    - Doctor & Lab: require license_code
    - Patient: require email → OTP sent
    """
    # --------- DOCTOR ---------
    if user.role == "doctor":
        if not user.license_code or user.license_code not in DOCTOR_LICENSES:
            raise HTTPException(status_code=400, detail="Invalid doctor license code")
        if get_user_by_username(db, user.username):
            raise HTTPException(status_code=400, detail="Username already exists")
        if db.query(UserModel).filter(UserModel.license_code == user.license_code).first():
            raise HTTPException(status_code=400, detail="License code already in use")

        db_user = UserModel(
            username=user.username,
            password=hash_password(user.password),
            full_name=user.full_name,
            role="doctor",
            is_doctor=True,
            is_verified=True,   # doctors verified via license
            license_code=user.license_code
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return UserOut(id=db_user.id, username=db_user.username, full_name=db_user.full_name, role=db_user.role)

    # --------- LAB ---------
    if user.role == "lab":
        if not user.license_code or user.license_code not in LAB_LICENSES:
            raise HTTPException(status_code=400, detail="Invalid lab license code")
        if get_user_by_username(db, user.username):
            raise HTTPException(status_code=400, detail="Username already exists")
        if db.query(UserModel).filter(UserModel.license_code == user.license_code).first():
            raise HTTPException(status_code=400, detail="License code already in use")

        db_user = UserModel(
            username=user.username,
            password=hash_password(user.password),
            full_name=user.full_name,
            role="lab",
            is_lab=True,
            is_verified=True,   # labs verified via license
            license_code=user.license_code
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return UserOut(id=db_user.id, username=db_user.username, full_name=db_user.full_name, role=db_user.role)

    # --------- PATIENT ---------
    if user.role == "patient":
        if not user.email:
            raise HTTPException(status_code=400, detail="Email is required for patient signup")
        if get_user_by_username(db, user.username):
            raise HTTPException(status_code=400, detail="Username already exists")
        if get_user_by_email(db, user.email):
            raise HTTPException(status_code=400, detail="Email already registered")

        otp = str(random.randint(100000, 999999))
        now = datetime.utcnow()

        db_user = UserModel(
            username=user.username,
            password=hash_password(user.password),
            full_name=user.full_name,
            role="patient",
            email=user.email,
            otp=otp,
            otp_created_at=now,
            is_verified=False
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        # Send OTP email in background
        from app.core.email import send_otp_email
        background_tasks.add_task(send_otp_email, user.email, otp)

        logger.info(f"OTP sent to {user.email} for user {user.username}")
        # NOTE: OTP is NOT returned in the response for security
        return {"message": f"OTP sent to {user.email}. Please verify to complete signup.", "otp_sent": True}

    raise HTTPException(status_code=400, detail="Invalid role. Must be 'patient', 'doctor', or 'lab'")


# --------------------------------------------------
# Verify OTP
# --------------------------------------------------
@router.post("/verify-otp", response_model=Dict)
def verify_otp(email: str, otp: str, db: Session = Depends(get_db)):
    """Verify 6-digit OTP and activate patient account."""
    user = get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=400, detail="Email not registered")

    if user.is_verified:
        return {"message": "Account already verified. Please login."}

    if not user.otp:
        raise HTTPException(status_code=400, detail="No OTP pending. Please signup again.")

    # Check expiry
    if user.otp_created_at:
        age = datetime.utcnow() - user.otp_created_at
        if age > timedelta(minutes=OTP_EXPIRY_MINUTES):
            user.otp = None
            user.otp_created_at = None
            db.commit()
            raise HTTPException(status_code=400, detail="OTP expired. Please signup again to get a new OTP.")

    if user.otp != otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    # Activate account
    user.is_verified = True
    user.otp = None
    user.otp_created_at = None
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "message": "Email verified successfully. You can now login.",
        "user": {"id": user.id, "username": user.username, "full_name": user.full_name, "role": user.role}
    }


# --------------------------------------------------
# Resend OTP
# --------------------------------------------------
@router.post("/resend-otp", response_model=Dict)
def resend_otp(email: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Resend a fresh OTP to the patient's email."""
    user = get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=400, detail="Email not registered")
    if user.is_verified:
        return {"message": "Account already verified."}

    otp = str(random.randint(100000, 999999))
    user.otp = otp
    user.otp_created_at = datetime.utcnow()
    db.add(user)
    db.commit()

    from app.core.email import send_otp_email
    background_tasks.add_task(send_otp_email, user.email, otp)

    return {"message": f"New OTP sent to {email}"}


# --------------------------------------------------
# Login
# --------------------------------------------------
@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Login using username + password (OAuth2 form).
    Returns JWT token. Only verified users can login.
    """
    db_user = get_user_by_username(db, form_data.username)
    if not db_user:
        raise HTTPException(status_code=400, detail="Invalid username or password")

    if not db_user.is_verified:
        raise HTTPException(
            status_code=403,
            detail="Account not verified. Please check your email for the OTP and verify your account."
        )

    if not verify_password(form_data.password, db_user.password):
        raise HTTPException(status_code=400, detail="Invalid username or password")

    token = create_access_token({"sub": db_user.username, "role": db_user.role})
    logger.info(f"User {db_user.username} logged in successfully")

    return {
        "message": "Login successful",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": db_user.id,
            "username": db_user.username,
            "full_name": db_user.full_name,
            "role": db_user.role
        }
    }


# --------------------------------------------------
# /me — Get current user info
# --------------------------------------------------
def get_current_user_from_token(authorization: str = Header(...), db: Session = Depends(get_db)):
    """Read user from Authorization: Bearer <token> header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.split(" ", 1)[1]
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token. Please login again.")

    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/me")
def me(current_user: UserModel = Depends(get_current_user_from_token)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "email": current_user.email
    }


# --------------------------------------------------
# Role-gated Dashboard stubs
# --------------------------------------------------
from app.core.role_checker import role_required

@router.get("/doctor/dashboard")
def doctor_dashboard(user=Depends(role_required("doctor"))):
    return {"message": "Welcome Doctor!", "user": user.username}

@router.get("/patient/dashboard")
def patient_dashboard(user=Depends(role_required("patient"))):
    return {"message": "Welcome Patient!", "user": user.username}

@router.get("/lab/dashboard")
def lab_dashboard(user=Depends(role_required("lab"))):
    return {"message": "Welcome Lab Tech!", "user": user.username}
