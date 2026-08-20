from pydantic import BaseModel
from typing import List, Optional

class PoolState(BaseModel):
    name: str
    health: str
    size: int
    allocated: int
    free: int