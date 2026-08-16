import logging
from pathlib import Path

current_dir = Path.cwd()
log_location = Path(current_dir / "tests/log/")

audit_logger = logging.getLogger("app.audit")
access_logger = logging.getLogger("app.access")


def test_access_log(create_log_dir):
    access_logger.info("test access log")
    with open (log_location / "access.log", 'r') as file:
        assert "test access log" in file.read()


def test_audit_log(create_log_dir):
    audit_logger.info("test audit log")
    with open (log_location / "audit.log", 'r') as file:
        assert "test audit log" in file.read()


def test_app_log(create_log_dir):
    logging.info("test app log")
    with open (log_location / "app.log", 'r') as file:
        assert "test app log" in file.read()