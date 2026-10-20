from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class CourseOption:
    code: str
    name: str
    category: str
    source: str


class CourseCatalogProvider(ABC):
    """Course catalog boundary for a future teaching-management-system adapter."""

    @abstractmethod
    def list_courses(
        self,
        *,
        major: str | None = None,
        grade: str | None = None,
        query: str | None = None,
    ) -> list[CourseOption]:
        raise NotImplementedError
