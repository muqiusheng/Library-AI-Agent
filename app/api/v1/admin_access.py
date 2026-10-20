from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import require_admin
from app.db.models import User
from app.schemas.common import ApiResponse, success_response

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/access-check", response_model=ApiResponse[dict[str, str]])
def access_check(
    request: Request, admin: Annotated[User, Depends(require_admin)]
) -> dict:
    return success_response(
        request.state.request_id,
        {"role": admin.role.value, "student_no": admin.student_no},
    )
