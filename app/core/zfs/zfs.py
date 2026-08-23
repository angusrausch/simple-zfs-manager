import json
import logging
from pathlib import Path

from app.core.zfs.utils import execute_zfs_command, execute_zfs_command_json
from app.core.zfs.models import DatasetState, DatasetType
from app.core.config import settings
from app.core.errors import ZFSCommandFailedError

audit_logger = logging.getLogger("app.audit")


async def create_dataset(uid: int, parent: str, dataset_name: str, create_parents: bool = False):
    full_dataset_name = parent + "/" + dataset_name
    command = [settings.ZFS_BINARY, "create", full_dataset_name]
    if create_parents:
        command.append("-p")

    await execute_zfs_command(uid, command, full_dataset_name)


async def destroy_dataset(uid: int, dataset_name: str, recursive: bool = False):
    command = [settings.ZFS_BINARY, "destroy", dataset_name]
    if recursive:
        command.append("-r")

    await execute_zfs_command(uid, command, dataset_name)


async def list_datasets(uid: int) -> list[DatasetState]:
    command = [settings.ZFS_BINARY, "list", "-pj"]
    dataset_data = await execute_zfs_command_json(uid, command)
    
    if not dataset_data or "datasets" not in dataset_data:
        return []

    return [_build_dataset_state(raw) for raw in dataset_data["datasets"].values()]



async def list_child_datasets(uid: int, dataset_name: str) -> list[DatasetState]:
    command = [settings.ZFS_BINARY, "list", "-pjr", dataset_name]
    dataset_data = await execute_zfs_command_json(uid, command)

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


async def create_snapshot(uid: int, dataset_name: str, snapshot_name: str, recursive: bool = False):
    full_snapshot_name = dataset_name + "@" + snapshot_name
    command = [settings.ZFS_BINARY, "snapshot", full_snapshot_name]
    if recursive:
        command.append("-r")

    await execute_zfs_command(uid, command, dataset_name)


async def restore_snapshot(uid: int, dataset_name: str, snapshot_name: str, destructive: bool = False):
    full_snapshot_name = dataset_name + "@" + snapshot_name
    command = [settings.ZFS_BINARY, "rollback", full_snapshot_name]
    if destructive:
        command.append("-r")

    await execute_zfs_command(uid, command, dataset_name)


async def list_snapshots(uid: int, dataset_name: str = None) -> list[DatasetState]:
    command = [settings.ZFS_BINARY, "list", "-pj", "-t", "snapshot"]
    if dataset_name:
        command.append(dataset_name)

    dataset_data = await execute_zfs_command_json(uid, command, dataset_name)
    
    if not dataset_data or "datasets" not in dataset_data:
        return []

    return [_build_dataset_state(raw) for raw in dataset_data["datasets"].values()]


def _build_dataset_state(data: dict) -> DatasetState:
    properties = data["properties"]
    return DatasetState(
        name=data["name"],
        type=DatasetType(data["type"]),
        pool=data["pool"],
        used=properties["used"]["value"] if properties["used"]["value"] != "-" else None,
        available=properties["available"]["value"] if properties["available"]["value"] != "-" else None,
        referenced=properties["referenced"]["value"] if properties["referenced"]["value"] != "-" else None,
        mountpoint=Path(properties["mountpoint"]["value"])
    )