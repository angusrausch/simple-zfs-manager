# app/core/system/logger.py
import logging
from pathlib import Path
from app.core.config import settings

def setup_logging():
    settings.LOG_LOCATION.parent.mkdir(parents=True, exist_ok=True)

    log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')

    if settings.DEBUG:
        logging_level = logging.DEBUG
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_formatter)
        console_handler.setLevel(logging_level)
    else:
        logging_level = logging.INFO

    file_handler = logging.FileHandler(
        settings.LOG_LOCATION,
        mode='a',
        encoding='utf-8'
    )
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging_level)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging_level)
    
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
    
    root_logger.addHandler(file_handler)
    if settings.DEBUG:
        root_logger.addHandler(console_handler)
