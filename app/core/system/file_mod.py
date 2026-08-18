from pathlib import Path
import logging

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
        audit_logger.error(f"[FILE] New lock file at {lock_file_path}")
        lock_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(lock_file_path, 'w', encoding='utf-8') as lock_file:
            lock_file.write(file_contents)
        return True
