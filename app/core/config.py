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
    
    # System Paths
    ZFS_BINARY: str = os.getenv("ZFS_BINARY_PATH", "/usr/sbin/zfs")
    ZPOOL_BINARY: str = os.getenv("ZPOOL_BINARY_PATH", "/usr/sbin/zpool")
    SUDO_BINARY: str = os.getenv("SUDO_BINARY_PATH", "/usr/bin/sudo")
    
    LOG_LOCATION: Path = Path(os.getenv("LOG_LOCATION", "/var/log/simple-zfs-viewer.log"))

settings = Settings()