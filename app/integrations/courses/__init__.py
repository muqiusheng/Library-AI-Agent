from app.integrations.courses.base import CourseCatalogProvider, CourseOption
from app.integrations.courses.local import LocalCourseCatalogProvider


def get_course_catalog_provider() -> CourseCatalogProvider:
    """Composition point for a future teaching-management-system provider."""
    return LocalCourseCatalogProvider()


__all__ = [
    "CourseCatalogProvider",
    "CourseOption",
    "LocalCourseCatalogProvider",
    "get_course_catalog_provider",
]
