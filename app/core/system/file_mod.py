from pathlib import Path
import logging
import os

from app.core.config import settings

audit_logger = logging.getLogger("app.audit")


def verify_file_integrity(file_path: Path) -> bool:
    abs_file_path = file_path.resolve()
    lock_file_path = settings.LOCK_FILE_PATH / abs_file_path.relative_to(abs_file_path.anchor)

    try:
        with open(abs_file_path, 'r', encoding='utf-8') as file:
            file_contents = file.read()
    except FileNotFoundError:
        audit_logger.error(f"[FILE] File Verification found input file does not exist: {abs_file_path}")
        raise FileNotFoundError(f"Input file does not exist: {abs_file_path}")

    if lock_file_path.exists():
        if lock_file_path.is_file():
            with open(lock_file_path, 'r', encoding='utf-8') as lock_file:
                lock_file_contents = lock_file.read()
            if file_contents == lock_file_contents:
                return True
            return False
        else:
            audit_logger.error(f"[FILE] File verification found folder exists at {lock_file_path}, this should be a file")
            raise FileExistsError(f"Folder exists at {lock_file_path}, this should be a file")
    else:
        audit_logger.info(f"[FILE] New lock file at {lock_file_path}")
        lock_file_path.parent.mkdir(parents=True, exist_ok=True)
        _safe_write(lock_file_path, file_contents)
        # with open(lock_file_path, 'w', encoding='utf-8') as lock_file:
        #     lock_file.write(file_contents)
        return True

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

