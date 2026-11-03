from pydantic import BaseModel, Field
from pathlib import Path

class NfsHost(BaseModel):
    host: str
    options: list[str]

class NfsShare(BaseModel):
    path: Path
    hosts: list[NfsHost]
