from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class VDevNode(BaseModel):
    name: str
    vdev_type: str
    state: str
    path: Optional[str] = None
    read_errors: int = 0
    write_errors: int = 0
    checksum_errors: int = 0
    vdevs: Optional[Dict[str, "VDevNode"]] = None 

class PoolState(BaseModel):
    name: str
    health: str
    
    size: int
    allocated: int
    free: int
    
    read_errors: int = 0
    write_errors: int = 0
    checksum_errors: int = 0
    
    vdev_tree: Optional[VDevNode] = None

class ImportablePools(BaseModel):
    name: str
    id: int
    healthy: bool