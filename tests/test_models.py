from sqlalchemy.orm import configure_mappers

from app.db.base import Base
from app.db.models import User

EXPECTED_TABLES = {
    "book_tags",
    "book_user_states",
    "books",
    "conversation_constraints",
    "conversations",
    "data_versions",
    "evaluation_records",
    "holdings",
    "import_batches",
    "import_issues",
    "learning_path_books",
    "learning_path_stages",
    "learning_paths",
    "messages",
    "notifications",
    "profile_memories",
    "recommendation_feedback",
    "recommendation_items",
    "recommendation_sets",
    "reservations",
    "system_settings",
    "user_profiles",
    "users",
}


def test_all_required_tables_are_registered() -> None:
    configure_mappers()
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_user_role_is_persisted_as_contract_value() -> None:
    role_type = User.__table__.c.role.type
    assert role_type.enums == ["student", "admin", "super_admin"]


def test_user_relationships_delete_owned_profile_data() -> None:
    assert "delete-orphan" in User.profile.property.cascade
    assert "delete-orphan" in User.memories.property.cascade
