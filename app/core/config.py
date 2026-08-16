# app/core/config.py
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "Simple ZFS Manager"
    
    # Network / Process
    PORT: int = int(os.getenv("PORT", 8080))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "insecure")

    # System Paths
    ZFS_BINARY: str = os.getenv("ZFS_BINARY_PATH", "/usr/sbin/zfs")
    ZPOOL_BINARY: str = os.getenv("ZPOOL_BINARY_PATH", "/usr/sbin/zpool")
    SUDO_BINARY: str = os.getenv("SUDO_BINARY_PATH", "/usr/bin/sudo")
    
settings = Settings()