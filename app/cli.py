import argparse
import json
import os
from pathlib import Path
from uuid import UUID

from sqlalchemy import desc, select

from app.db.models import DataVersion, DataVersionStatus
from app.db.session import SessionLocal
from app.pipelines.import_excel import ExcelLibraryImporter, report_as_dict
from app.pipelines.index import BookIndexService
from app.pipelines.tag import RuleTaggingService
from app.services.admin_seed import seed_admin
from app.services.demo_seed import reset_demo_activity, seed_demo_accounts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bookpath")
    subparsers = parser.add_subparsers(dest="command", required=True)

    seed_parser = subparsers.add_parser("seed-admin", help="create the initial admin account")
    seed_parser.add_argument("--student-no", required=True)
    seed_parser.add_argument("--display-name", default="系统管理员")
    seed_parser.add_argument(
        "--password-env",
        default="BOOKPATH_ADMIN_PASSWORD",
        help="environment variable containing the password",
    )
    import_parser = subparsers.add_parser(
        "import-library", help="import and aggregate library Excel"
    )
    import_parser.add_argument("file", type=Path)
    import_parser.add_argument(
        "--draft", action="store_true", help="do not publish the data version"
    )
    tag_parser = subparsers.add_parser("tag-books", help="generate rule tags for books")
    tag_parser.add_argument(
        "--version", type=UUID, help="data version UUID; defaults to latest published"
    )
    tag_parser.add_argument("--limit", type=int)
    index_parser = subparsers.add_parser(
        "build-index", help="build the versioned Chroma book index"
    )
    index_parser.add_argument(
        "--version", type=UUID, help="data version UUID; defaults to latest published"
    )
    index_parser.add_argument("--limit", type=int)
    demo_parser = subparsers.add_parser("seed-demo", help="create two idempotent demo students")
    demo_parser.add_argument("--password-env", default="BOOKPATH_DEMO_PASSWORD")
    subparsers.add_parser(
        "reset-demo", help="clear demo activity but preserve accounts and library"
    )
    return parser


def resolve_data_version(session, requested: UUID | None) -> UUID:
    if requested is not None:
        version = session.get(DataVersion, requested)
    else:
        version = session.scalar(
            select(DataVersion)
            .where(DataVersion.status == DataVersionStatus.PUBLISHED)
            .order_by(desc(DataVersion.published_at), desc(DataVersion.created_at))
            .limit(1)
        )
    if version is None:
        raise SystemExit("no matching data version; import and publish library data first")
    return version.id


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "seed-admin":
        password = os.getenv(args.password_env)
        if password is None:
            raise SystemExit(f"missing password environment variable: {args.password_env}")
        with SessionLocal() as session:
            result = seed_admin(
                session,
                student_no=args.student_no,
                password=password,
                display_name=args.display_name,
            )
        action = "created" if result.created else "already exists"
        print(f"admin {result.student_no}: {action}")
        return 0
    if args.command == "import-library":
        with SessionLocal() as session:
            report = ExcelLibraryImporter(session).import_file(args.file, publish=not args.draft)
        print(json.dumps(report_as_dict(report), ensure_ascii=False, indent=2))
        return 0
    if args.command in {"tag-books", "build-index"}:
        with SessionLocal() as session:
            version_id = resolve_data_version(session, args.version)
            if args.command == "tag-books":
                count = RuleTaggingService(session).run(version_id, limit=args.limit)
            else:
                count = BookIndexService(session).build(version_id, limit=args.limit)
        print(
            json.dumps({"data_version_id": str(version_id), "processed": count}, ensure_ascii=False)
        )
        return 0
    if args.command == "seed-demo":
        password = os.getenv(args.password_env)
        if password is None or not 8 <= len(password) <= 16:
            raise SystemExit(f"missing or short password environment variable: {args.password_env}")
        with SessionLocal() as session:
            result = seed_demo_accounts(session, password)
        print(
            json.dumps({"created": result.created, "existing": result.existing}, ensure_ascii=False)
        )
        return 0
    if args.command == "reset-demo":
        with SessionLocal() as session:
            count = reset_demo_activity(session)
        print(json.dumps({"reset_users": count}, ensure_ascii=False))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
