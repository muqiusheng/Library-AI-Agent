from enum import StrEnum


def enum_values[EnumT: StrEnum](enum_class: type[EnumT]) -> list[str]:
    return [item.value for item in enum_class]


class UserRole(StrEnum):
    STUDENT = "student"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class DifficultyPreference(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    PROGRESSIVE = "progressive"


class MemorySource(StrEnum):
    REGISTRATION = "registration"
    CONVERSATION = "conversation"
    MANUAL = "manual"
    FEEDBACK = "feedback"


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageType(StrEnum):
    TEXT = "text"
    RECOMMENDATION = "recommendation"
    PATH = "path"
    SYSTEM = "system"


class DataVersionStatus(StrEnum):
    DRAFT = "draft"
    PROCESSING = "processing"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    FAILED = "failed"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class BookUserStateValue(StrEnum):
    WANT_TO_READ = "want_to_read"
    READING = "reading"
    COMPLETED = "completed"


class FeedbackType(StrEnum):
    LIKE = "like"
    NOT_INTERESTED = "not_interested"
    TOO_HARD = "too_hard"
    TOO_EASY = "too_easy"
    READ = "read"


class LearningPathStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ReservationStatus(StrEnum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    COMPLETED = "completed"


class ImportStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class IssueStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    IGNORED = "ignored"
