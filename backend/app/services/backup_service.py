import datetime
import shutil
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.time import utcnow
from app.services import settings_service

_DEFAULT_RETENTION = 7
_BACKUP_DIR_NAME = "backups"


def _db_path() -> Path | None:
    url = settings.database_url
    prefix = "sqlite+aiosqlite:///"
    if not url.startswith(prefix):
        return None
    return Path(url[len(prefix):])


def _backup_dir(db_path: Path) -> Path:
    directory = db_path.parent / _BACKUP_DIR_NAME
    directory.mkdir(parents=True, exist_ok=True)
    return directory


async def run_backup_now(session: AsyncSession) -> Path | None:
    db_path = _db_path()
    if db_path is None or not db_path.exists():
        return None
    backup_dir = _backup_dir(db_path)
    timestamp = utcnow().strftime("%Y%m%d-%H%M%S")
    destination = backup_dir / f"areses-{timestamp}.db"
    shutil.copy2(db_path, destination)
    await _prune_old_backups(session, backup_dir)
    return destination


async def _prune_old_backups(session: AsyncSession, backup_dir: Path) -> None:
    retention_raw = await settings_service.get_global_setting(
        session, "backupRetentionCount"
    )
    try:
        retention = int(retention_raw) if retention_raw else _DEFAULT_RETENTION
    except ValueError:
        retention = _DEFAULT_RETENTION

    backups = sorted(backup_dir.glob("areses-*.db"), key=lambda p: p.name, reverse=True)
    for stale in backups[retention:]:
        stale.unlink(missing_ok=True)


async def maybe_run_scheduled_backup(session: AsyncSession) -> None:
    enabled = await settings_service.get_global_setting(session, "backupEnabled")
    if enabled != "true":
        return
    await run_backup_now(session)


def list_backups() -> list[dict]:
    db_path = _db_path()
    if db_path is None:
        return []
    backup_dir = db_path.parent / _BACKUP_DIR_NAME
    if not backup_dir.exists():
        return []
    return sorted(
        (
            {
                "filename": p.name,
                "size_bytes": p.stat().st_size,
                "created_at": datetime.datetime.utcfromtimestamp(
                    p.stat().st_mtime
                ).isoformat(),
            }
            for p in backup_dir.glob("areses-*.db")
        ),
        key=lambda entry: entry["filename"],
        reverse=True,
    )


def delete_backup(filename: str) -> bool:
    db_path = _db_path()
    if db_path is None:
        return False
    backup_dir = db_path.parent / _BACKUP_DIR_NAME
    candidate = backup_dir / filename
    if candidate.parent != backup_dir:
        return False
    if not candidate.name.startswith("areses-") or not candidate.name.endswith(".db"):
        return False
    if not candidate.exists():
        return False
    candidate.unlink()
    return True
