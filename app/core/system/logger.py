# app/core/system/logger.py
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from app.core.config import settings

def setup_logging():
    log_dir = settings.LOG_LOCATION.parent
    log_dir.mkdir(parents=True, exist_ok=True)

    access_log_path = log_dir / "access.log"
    audit_log_path = log_dir / "audit.log"
    app_log_path = settings.LOG_LOCATION

    log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')

    logging_level = logging.DEBUG if settings.DEBUG else logging.INFO

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging_level)

    max_bytes = 10 * 1024 * 1024
    backup_count = 5

    main_file_handler = RotatingFileHandler(app_log_path, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8')
    main_file_handler.setFormatter(log_formatter)
    main_file_handler.setLevel(logging_level)

    access_file_handler = RotatingFileHandler(access_log_path, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8')
    access_file_handler.setFormatter(log_formatter)
    access_file_handler.setLevel(logging_level)

    audit_file_handler = RotatingFileHandler(audit_log_path, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8')
    audit_file_handler.setFormatter(log_formatter)
    audit_file_handler.setLevel(logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging_level)
    root_logger.handlers.clear()
    root_logger.addHandler(main_file_handler)
    if settings.DEBUG:
        root_logger.addHandler(console_handler)

    access_logger = logging.getLogger("app.access")
    access_logger.setLevel(logging_level)
    access_logger.handlers.clear()
    access_logger.addHandler(access_file_handler)
    access_logger.propagate = False
    if settings.DEBUG:
        access_logger.addHandler(console_handler)

    audit_logger = logging.getLogger("app.audit")
    audit_logger.setLevel(logging_level)
    audit_logger.handlers.clear()
    audit_logger.addHandler(audit_file_handler)
    audit_logger.propagate = False
    if settings.DEBUG:
        audit_logger.addHandler(console_handler)

    for uvicorn_logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
        u_logger = logging.getLogger(uvicorn_logger_name)
        u_logger.handlers.clear()
        u_logger.addHandler(access_file_handler)
        u_logger.propagate = False