from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from pathlib import Path

class SmbShare(BaseModel):
    name: str
    path: Optional[Path] = None
    browsable: bool
    read_only: bool
    public: bool
    users: list[str]
    force_user: Optional[str] = None
    create_mask: int
    dir_mask: int