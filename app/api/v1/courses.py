from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.integrations.courses import CourseCatalogProvider, get_course_catalog_provider
from app.schemas.catalog import CourseOptionRead
from app.schemas.common import ApiResponse, success_response

router = APIRouter(prefix="/api/v1/catalog/courses", tags=["course-catalog"])


@router.get("", response_model=ApiResponse[list[CourseOptionRead]])
def list_courses(
    request: Request,
    provider: Annotated[CourseCatalogProvider, Depends(get_course_catalog_provider)],
    major: str | None = Query(default=None, max_length=150),
    grade: str | None = Query(default=None, max_length=50),
    query: str | None = Query(default=None, max_length=100),
) -> dict:
    # This dependency boundary is intentionally small so a teaching-system adapter
    # can replace the local catalog without changing the registration contract.
    values = provider.list_courses(
        major=major,
        grade=grade,
        query=query,
    )
    return success_response(
        request.state.request_id,
        [CourseOptionRead.model_validate(value, from_attributes=True) for value in values],
    )
