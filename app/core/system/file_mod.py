from pathlib import Path
import logging
import os

from app.core.config import settings
from app.core.errors import MissingInputFileError, LockFileMismatchError, LockPathBlockedError, PathBlockedError, CannotWriteError

audit_logger = logging.getLogger("app.audit")


def verify_file_integrity(file_path: Path):
    lock_file_path = _find_lock_path(file_path)

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            file_contents = file.read()
    except FileNotFoundError:
        raise MissingInputFileError.log_and_raise(
            f"File Verification found input file does not exist: {file_path}"
        )

    if lock_file_path.exists():
        if lock_file_path.is_file():
            with open(lock_file_path, 'r', encoding='utf-8') as lock_file:
                lock_file_contents = lock_file.read()
            if file_contents != lock_file_contents:
                raise LockFileMismatchError.log_and_raise(
                    f"File verification failed on file {file_path}"
                )
        else:
            raise LockPathBlockedError.log_and_raise(
                f"File verification found folder exists at {lock_file_path}, this should be a file"
            )
    else:
        audit_logger.info(f"[FILE] New lock file at {lock_file_path}")
        lock_file_path.parent.mkdir(parents=True, exist_ok=True)
        _safe_write(lock_file_path, file_contents)


def write_file(file_path: Path, contents: str):
    old_contents = None
    if file_path.is_file():
        verify_file_integrity(file_path)
        with open(file_path, 'r', encoding="utf-8") as f:
            old_contents = f.read()
    elif file_path.exists():
        raise PathBlockedError.log_and_raise(
            f"File write found folder exists at {file_path}, this should be a file"
        )

    try:
        _safe_write(file_path, contents)
    except Exception as e:
        raise CannotWriteError.log_and_raise(f"Failed to write file {file_path}. Error: {e}")

    lock_file_path = _find_lock_path(file_path)
    try:
        _safe_write(lock_file_path, contents)
    except Exception as e:
        try:
            if old_contents:
                _safe_write(file_path, old_contents)
            else:
                file_path.unlink()
        except Exception as rollback_err:
            audit_logger.warning(f"[FILE] Rollback to original contents failed: {rollback_err}")
            
        raise CannotWriteError.log_and_raise(f"Failed to write file {lock_file_path}. Error: {e}")

    verify_file_integrity(file_path)


def _find_lock_path(file_path: Path) -> Path:
    abs_file_path = file_path.resolve()
    return settings.LOCK_FILE_PATH / abs_file_path.relative_to(abs_file_path.anchor)


def _safe_write(file_path: Path, contents: str):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    shadow_file_name = f".{file_path.name}.shadow"
    shadow_file_path = file_path.parent / shadow_file_name

    try:
        with open(shadow_file_path, 'w', encoding='utf-8') as shadow_file:
            shadow_file.write(contents)
            shadow_file.flush()
            os.fsync(shadow_file.fileno())
    except Exception as e:
        shadow_file_path.unlink(missing_ok=True)
        audit_logger.error(f"[FILE] Safe write data phase failed: {e}")
        raise e

    try:
        shadow_file_path.replace(file_path)
        
        dir_fd = os.open(file_path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
            
    except Exception as e:
        audit_logger.error(f"[FILE] Safe write metadata sync phase failed: {e}")
        raise e
