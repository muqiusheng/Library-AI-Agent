from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.security import create_access_token
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import (
    LoginRequest,
    LogoutResponse,
    RegisterRequest,
    TokenResponse,
    UserSummary,
)
from app.schemas.common import ApiResponse, success_response
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=ApiResponse[UserSummary],
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: RegisterRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    user = AuthService(session).register(payload)
    return success_response(request.state.request_id, UserSummary.model_validate(user))


@router.post("/login", response_model=ApiResponse[TokenResponse])
def login(
    payload: LoginRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    user = AuthService(session).authenticate(
        payload.student_no, payload.password.get_secret_value()
    )
    token, expires_in = create_access_token(user_id=user.id, role=user.role.value)
    data = TokenResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserSummary.model_validate(user),
    )
    return success_response(request.state.request_id, data)


@router.get("/me", response_model=ApiResponse[UserSummary])
def me(
    request: Request, current_user: Annotated[User, Depends(get_current_user)]
) -> dict:
    return success_response(request.state.request_id, UserSummary.model_validate(current_user))


from app.schemas.auth import UserUpdateRequest

@router.put("/me", response_model=ApiResponse[UserSummary])
def update_me(
    payload: UserUpdateRequest,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    if payload.display_name is not None:
        current_user.display_name = payload.display_name
    session.commit()
    session.refresh(current_user)
    return success_response(request.state.request_id, UserSummary.model_validate(current_user))


from fastapi import UploadFile, File
import shutil
import os
from pathlib import Path
from app.core.config import get_settings
from uuid import uuid4
from fastapi.responses import JSONResponse

@router.post("/me/avatar", response_model=ApiResponse[UserSummary])
def upload_avatar(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(...),
) -> dict:
    settings = get_settings()
    upload_dir = Path(settings.import_upload_directory) / "avatars"
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    ext = os.path.splitext(file.filename or "")[1]
    filename = f"{uuid4()}{ext}"
    file_path = upload_dir / filename
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # In a real app we might upload to S3 or have a static file server route.
    # Here we can assume FastAPI serves static files, or we just save the local path
    # Wait, does the app serve static files? 
    # Let's save the relative URL that can be fetched later. If it's not served, we will need to serve it.
    current_user.avatar_url = f"/api/v1/auth/avatars/{filename}"
    session.commit()
    session.refresh(current_user)
    return success_response(request.state.request_id, UserSummary.model_validate(current_user))

from fastapi.responses import FileResponse
@router.get("/avatars/{filename}")
def get_avatar(filename: str):
    settings = get_settings()
    file_path = Path(settings.import_upload_directory) / "avatars" / filename
    if file_path.exists():
        return FileResponse(file_path)
    return JSONResponse(status_code=404, content={"detail": "Avatar not found"})


@router.post("/logout", response_model=ApiResponse[LogoutResponse])
def logout(request: Request, _: Annotated[User, Depends(get_current_user)]) -> dict:
    return success_response(request.state.request_id, LogoutResponse())
