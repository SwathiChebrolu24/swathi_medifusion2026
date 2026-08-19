from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.security import OAuth2PasswordRequestForm
from typing import Dict, Union
from sqlalchemy.orm import Session
import logging

from app.schemas.user_schema import UserCreate, UserOut
from app.models.user import User as UserModel
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token
from app.core.role_checker import role_required

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth"])
DOCTOR_LICENSES = [f"DOC{str(i).zfill(3)}" for i in range(1, 22)]
LAB_LICENSES = [f"LAB{str(i).zfill(3)}" for i in range(1, 22)]


def get_user_by_username(db: Session, username: str):
    return db.query(UserModel).filter(UserModel.username == username).first()


@router.post("/signup", response_model=Union[UserOut, Dict])
def signup(user: UserCreate, db: Session = Depends(get_db)):
    if user.role == "doctor":
        if not user.license_code or user.license_code not in DOCTOR_LICENSES:
            raise HTTPException(status_code=400, detail="Invalid doctor license code")
        if get_user_by_username(db, user.username):
            raise HTTPException(status_code=400, detail="Username already exists")
        if db.query(UserModel).filter(UserModel.license_code == user.license_code).first():
            raise HTTPException(status_code=400, detail="License code already in use")
        db_user = UserModel(username=user.username, password=hash_password(user.password), full_name=user.full_name, role="doctor", is_doctor=True, is_verified=True, license_code=user.license_code)

    elif user.role == "lab":
        if not user.license_code or user.license_code not in LAB_LICENSES:
            raise HTTPException(status_code=400, detail="Invalid lab license code")
        if get_user_by_username(db, user.username):
            raise HTTPException(status_code=400, detail="Username already exists")
        if db.query(UserModel).filter(UserModel.license_code == user.license_code).first():
            raise HTTPException(status_code=400, detail="License code already in use")
        db_user = UserModel(username=user.username, password=hash_password(user.password), full_name=user.full_name, role="lab", is_lab=True, is_verified=True, license_code=user.license_code)

    elif user.role == "patient":
        existing_user = get_user_by_username(db, user.username)
        if existing_user and existing_user.role == "patient" and not existing_user.is_verified:
            existing_user.password = hash_password(user.password)
            existing_user.full_name = user.full_name
            existing_user.is_verified = True
            db.commit()
            db.refresh(existing_user)
            return UserOut(id=existing_user.id, username=existing_user.username, full_name=existing_user.full_name, role=existing_user.role)
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already exists")
        db_user = UserModel(username=user.username, password=hash_password(user.password), full_name=user.full_name, role="patient", is_verified=True)

    else:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'patient', 'doctor', or 'lab'")

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return UserOut(id=db_user.id, username=db_user.username, full_name=db_user.full_name, role=db_user.role)


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    db_user = get_user_by_username(db, form_data.username)
    if not db_user or not verify_password(form_data.password, db_user.password):
        raise HTTPException(status_code=400, detail="Invalid username or password")
    token = create_access_token({"sub": db_user.username, "role": db_user.role})
    return {"message": "Login successful", "access_token": token, "token_type": "bearer", "user": {"id": db_user.id, "username": db_user.username, "full_name": db_user.full_name, "role": db_user.role}}


def get_current_user_from_token(authorization: str = Header(...), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    payload = decode_access_token(authorization.split(" ", 1)[1])
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
    return {"id": current_user.id, "username": current_user.username, "full_name": current_user.full_name, "role": current_user.role, "email": current_user.email}


@router.get("/doctor/dashboard")
def doctor_dashboard(user=Depends(role_required("doctor"))):
    return {"message": "Welcome Doctor!", "user": user.username}


@router.get("/patient/dashboard")
def patient_dashboard(user=Depends(role_required("patient"))):
    return {"message": "Welcome Patient!", "user": user.username}


@router.get("/lab/dashboard")
def lab_dashboard(user=Depends(role_required("lab"))):
    return {"message": "Welcome Lab Tech!", "user": user.username}
