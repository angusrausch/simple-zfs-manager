import json
import logging
from pathlib import Path

from app.core.zfs.utils import execute_zfs_command, execute_zfs_command_json
from app.core.zfs.models import DatasetState
from app.core.config import settings
from app.core.errors import ZFSCommandFailedError

audit_logger = logging.getLogger("app.audit")


async def create_dataset(uid: int, parent: str, dataset_name: str, create_parents: bool = False):
    full_dataset_name = parent + "/" + dataset_name
    command = [settings.ZFS_BINARY, "create", full_dataset_name]
    if create_parents:
        command.append("-p")

    await execute_zfs_command(uid, command, full_dataset_name)


async def destroy_dataset(uid: int, dataset_name: str):
    command = [settings.ZFS_BINARY, "destroy", dataset_name]

    await execute_zfs_command(uid, command, dataset_name)


async def list_datasets(uid: int) -> list[DatasetState]:
    command = [settings.ZFS_BINARY, "list", "-pj"]
    dataset_data = await execute_zfs_command_json(uid, command)
    
    if not dataset_data or "datasets" not in dataset_data:
        return []

    return [_build_dataset_state(raw) for raw in dataset_data["datasets"].values()]


async def list_dataset(uid: int, dataset_name: str) -> DatasetState:
    command = [settings.ZFS_BINARY, "list", "-pj", dataset_name]
    dataset_data = await execute_zfs_command_json(uid, command)
    return _build_dataset_state(dataset_data["datasets"][dataset_name])


async def rename_dataset(uid: int, old_name: str, new_name: str, create_parents: bool = False):
    command = [settings.ZFS_BINARY, "rename", old_name, new_name]
    if create_parents:
        command.append("-p")

    await execute_zfs_command(uid, command, old_name, new_name)


def _build_dataset_state(data: dict) -> DatasetState:
    properties = data["properties"]
    return DatasetState(
        name=data["name"],
        type=data["type"],
        pool=data["pool"],
        used=properties["used"]["value"],
        available=properties["available"]["value"],
        referenced=properties["referenced"]["value"],
        mountpoint=Path(properties["mountpoint"]["value"])
    )