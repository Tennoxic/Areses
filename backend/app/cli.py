import argparse
import asyncio
import shutil
import sys
from pathlib import Path

from sqlalchemy import delete, select, text

from app.core.config import settings
from app.core.security import hash_password
from app.db.models import (
    Folder,
    PasswordResetToken,
    SavedSearch,
    Source,
    Subscription,
    User,
    UserArticleState,
    UserSession,
)
from app.db.session import async_session_maker
from app.services import scheduler


async def cmd_create_admin(args: argparse.Namespace) -> None:
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.username == args.username))
        if result.scalar_one_or_none() is not None:
            print(f"user '{args.username}' already exists", file=sys.stderr)
            sys.exit(1)
        user = User(
            username=args.username,
            email=args.email,
            password_hash=hash_password(args.password),
            is_admin=True,
        )
        session.add(user)
        await session.commit()
        print(f"created admin user '{args.username}' (id={user.id})")


async def cmd_list_users(args: argparse.Namespace) -> None:
    async with async_session_maker() as session:
        result = await session.execute(select(User))
        for user in result.scalars().all():
            role = "admin" if user.is_admin else "user"
            print(f"{user.id}\t{user.username}\t{user.email}\t{role}")


async def cmd_delete_user(args: argparse.Namespace) -> None:
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.username == args.username))
        user = result.scalar_one_or_none()
        if user is None:
            print(f"user '{args.username}' not found", file=sys.stderr)
            sys.exit(1)
        if user.is_admin:
            admin_count = await session.execute(select(User).where(User.is_admin.is_(True)))
            if len(admin_count.scalars().all()) <= 1:
                print("cannot delete the last admin", file=sys.stderr)
                sys.exit(1)
        user_id = user.id
        await session.execute(delete(UserSession).where(UserSession.user_id == user_id))
        await session.execute(
            delete(PasswordResetToken).where(PasswordResetToken.user_id == user_id)
        )
        await session.execute(
            delete(UserArticleState).where(UserArticleState.user_id == user_id)
        )
        await session.execute(delete(Subscription).where(Subscription.user_id == user_id))
        await session.execute(delete(Folder).where(Folder.user_id == user_id))
        await session.execute(delete(SavedSearch).where(SavedSearch.user_id == user_id))
        await session.delete(user)
        await session.commit()
        print(f"deleted user '{args.username}'")


async def cmd_reset_password(args: argparse.Namespace) -> None:
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.username == args.username))
        user = result.scalar_one_or_none()
        if user is None:
            print(f"user '{args.username}' not found", file=sys.stderr)
            sys.exit(1)
        user.password_hash = hash_password(args.new_password)
        await session.execute(delete(UserSession).where(UserSession.user_id == user.id))
        await session.commit()
        print(f"password reset for '{args.username}', all sessions invalidated")


def _db_path() -> Path:
    url = settings.database_url
    prefix = "sqlite+aiosqlite:///"
    if not url.startswith(prefix):
        print("backup/restore only supported for local SQLite databases", file=sys.stderr)
        sys.exit(1)
    return Path(url[len(prefix):])


def cmd_backup(args: argparse.Namespace) -> None:
    source = _db_path()
    destination = Path(args.path)
    shutil.copy2(source, destination)
    print(f"backed up {source} -> {destination}")


def cmd_restore(args: argparse.Namespace) -> None:
    source = Path(args.path)
    destination = _db_path()
    if not source.exists():
        print(f"backup file not found: {source}", file=sys.stderr)
        sys.exit(1)
    shutil.copy2(source, destination)
    print(f"restored {source} -> {destination}")


async def cmd_list_feeds(args: argparse.Namespace) -> None:
    async with async_session_maker() as session:
        result = await session.execute(select(Source))
        for source in result.scalars().all():
            state = "broken" if source.consecutive_fail_count >= 5 else "ok"
            active = "active" if source.active else "inactive"
            print(f"{source.id}\t{source.url}\t{state}\t{active}\t{source.last_fetch_status}")


async def cmd_refresh_feed(args: argparse.Namespace) -> None:
    await scheduler.trigger_fetch_now(args.source_id)
    print(f"refreshed source {args.source_id}")


async def cmd_refresh_all(args: argparse.Namespace) -> None:
    async with async_session_maker() as session:
        result = await session.execute(select(Source.id).where(Source.active.is_(True)))
        source_ids = [row[0] for row in result.all()]
    for source_id in source_ids:
        await scheduler.trigger_fetch_now(source_id)
        print(f"refreshed source {source_id}")
    print(f"done, {len(source_ids)} sources refreshed")


async def cmd_backfill_security(args: argparse.Namespace) -> None:
    from app.core.crypto import encrypt_secret, is_already_encrypted
    from app.db.models import Article
    from app.services.sanitizer import sanitize_plain_text
    from app.services.settings_service import _SENSITIVE_KEYS

    async with async_session_maker() as session:
        titles_fixed = 0
        result = await session.execute(select(Article))
        for article in result.scalars().all():
            clean_title = sanitize_plain_text(article.title) or "(untitled)"
            clean_author = sanitize_plain_text(article.author) if article.author else None
            if clean_title != article.title or clean_author != article.author:
                article.title = clean_title
                article.author = clean_author
                titles_fixed += 1

        secrets_fixed = 0
        result = await session.execute(select(Source).where(Source.http_password.is_not(None)))
        for source in result.scalars().all():
            if not is_already_encrypted(source.http_password):
                source.http_password = encrypt_secret(source.http_password)
                secrets_fixed += 1

        from app.db.models import Setting

        for key in _SENSITIVE_KEYS:
            result = await session.execute(
                select(Setting.value)
                .where(Setting.user_id.is_(None), Setting.key == key)
                .order_by(text("rowid DESC"))
                .limit(1)
            )
            current_value = result.scalar_one_or_none()
            if current_value is None or is_already_encrypted(current_value):
                continue
            await session.execute(
                delete(Setting).where(Setting.user_id.is_(None), Setting.key == key)
            )
            session.add(Setting(user_id=None, key=key, value=encrypt_secret(current_value)))
            secrets_fixed += 1

        await session.commit()

    print(f"sanitized {titles_fixed} article title/author field(s)")
    print(f"encrypted {secrets_fixed} previously-plaintext secret(s)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="areses-cli", description="ARESES administration CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p = subparsers.add_parser("create-admin", help="Create an admin user")
    p.add_argument("username")
    p.add_argument("email")
    p.add_argument("password")
    p.set_defaults(func=cmd_create_admin, is_async=True)

    p = subparsers.add_parser("list-users", help="List all users")
    p.set_defaults(func=cmd_list_users, is_async=True)

    p = subparsers.add_parser("delete-user", help="Delete a user and all their data")
    p.add_argument("username")
    p.set_defaults(func=cmd_delete_user, is_async=True)

    p = subparsers.add_parser("reset-password", help="Reset a user's password")
    p.add_argument("username")
    p.add_argument("new_password")
    p.set_defaults(func=cmd_reset_password, is_async=True)

    p = subparsers.add_parser("backup", help="Copy the SQLite database file to a backup path")
    p.add_argument("path")
    p.set_defaults(func=cmd_backup, is_async=False)

    p = subparsers.add_parser("restore", help="Restore the SQLite database file from a backup path")
    p.add_argument("path")
    p.set_defaults(func=cmd_restore, is_async=False)

    p = subparsers.add_parser("list-feeds", help="List all feed sources and their status")
    p.set_defaults(func=cmd_list_feeds, is_async=True)

    p = subparsers.add_parser("refresh-feed", help="Trigger an immediate scan of one source")
    p.add_argument("source_id", type=int)
    p.set_defaults(func=cmd_refresh_feed, is_async=True)

    p = subparsers.add_parser("refresh-all", help="Trigger an immediate scan of all active sources")
    p.set_defaults(func=cmd_refresh_all, is_async=True)

    p = subparsers.add_parser(
        "backfill-security",
        help="Sanitize article titles and encrypt plaintext secrets written before this audit's fixes (safe to re-run)",
    )
    p.set_defaults(func=cmd_backfill_security, is_async=True)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.is_async:
        asyncio.run(args.func(args))
    else:
        args.func(args)


if __name__ == "__main__":
    main()
