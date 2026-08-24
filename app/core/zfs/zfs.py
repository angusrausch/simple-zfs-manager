import json
import logging
from pathlib import Path
import tempfile

from app.core.zfs.utils import execute_zfs_command, execute_zfs_command_json
from app.core.zfs.models import DatasetState, DatasetType
from app.core.config import settings
from app.core.errors import ZFSCommandFailedError

audit_logger = logging.getLogger("app.audit")


async def create_dataset(uid: int, parent: str, dataset_name: str, create_parents: bool = False, encryption: str = None):
    full_dataset_name = parent + "/" + dataset_name
    command = [settings.ZFS_BINARY, "create", full_dataset_name]
    if create_parents:
        command.append("-p")

    if not encryption:
        await execute_zfs_command(uid, command, full_dataset_name)
    else:
        with tempfile.NamedTemporaryFile(delete=True) as password_file:
            password_file.write(encryption.encode("utf-8"))
            password_file.flush()

            command += ["-o", "encryption=on", "-o", "keyformat=passphrase", "-o", f"keylocation=file:///{password_file.name}"]

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


async def mount_dataset(uid: int, dataset_name: str, recursive: bool = False, encryption: str = None):
    command = [settings.ZFS_BINARY, "mount", dataset_name]
    if recursive:
        command.append("-R")
    if encryption: 
        await load_key(uid, dataset_name, encryption)
    await execute_zfs_command(uid, command)


async def unmount_dataset(uid: int, dataset_name: str, force: bool = False, unload_key: bool = False):
    command = [settings.ZFS_BINARY, "unmount", dataset_name]
    if force:
        command.append("-f")
    if unload_key:
        command.append("-u")

    await execute_zfs_command(uid, command)


async def load_key(uid: int, dataset_name: str, key: str):
    with tempfile.NamedTemporaryFile(delete=True) as password_file:
        password_file.write(key.encode("utf-8"))
        password_file.flush()

        command = [settings.ZFS_BINARY, "load-key", dataset_name, "-L", f"file:///{password_file.name}"]

        await execute_zfs_command(uid, command, dataset_name)


async def unload_key(uid: int, dataset_name: str, recursive: bool = False):
    command = [settings.ZFS_BINARY, "unload-key", dataset_name]
    if recursive:
        command.append("-r")
    
    await execute_zfs_command(uid, command, dataset_name)


async def get_dataset(uid: int, dataset_name: str) -> DatasetState:
    command = [settings.ZFS_BINARY, "get", "all", "-pj", dataset_name]
    
    dataset_data = await execute_zfs_command_json(uid, command, dataset_name)

    return _build_dataset_state(dataset_data["datasets"][dataset_name], detailed=True)


async def get_datasets(uid: int) -> DatasetState:
    command = [settings.ZFS_BINARY, "get", "all", "-pj"]
    
    dataset_data = await execute_zfs_command_json(uid, command)

    return [_build_dataset_state(raw, detailed=True) for raw in dataset_data["datasets"].values()]


def _value_if_key_exists(dict: dict, key: str, sub_key: str = None, bool_comparision_value: bool = None, parse: type = None):            
    if not key in dict:
        return
    value = dict[key]
    if sub_key:
        value = value[sub_key]

    if bool_comparision_value:
        return value == bool_comparision_value
    if parse:
        try:
            return parse(value)
        except ValueError:
            return None
    return value

def _build_dataset_state(data: dict, detailed: bool = False) -> DatasetState:
    properties = data["properties"]
    state = DatasetState(
        name=data["name"],
        type=DatasetType(data["type"]),
        pool=data["pool"],
    )
    state.mountpoint = _value_if_key_exists(properties, "mountpoint", "value", parse=Path)
    state.used = _value_if_key_exists(properties, "used", "value", parse=int)
    state.available = _value_if_key_exists(properties, "available", "value", parse=int)
    state.referenced = _value_if_key_exists(properties, "referenced", "value", parse=int)

    if detailed:
        state.mounted = _value_if_key_exists(properties, "mounted", "value", bool_comparision_value="yes")
        state.quota = _value_if_key_exists(properties, "quota", "value", parse=int)
        state.refquota = _value_if_key_exists(properties, "refquota", "value", parse=int)
        state.reservation = _value_if_key_exists(properties, "reservation", "value", parse=int)
        state.refreservation = _value_if_key_exists(properties, "refreservation", "value", parse=int)
        state.encrypted = not _value_if_key_exists(properties, "encryption", "value", bool_comparision_value="off")
        state.compression = _value_if_key_exists(properties, "compression", "value", bool_comparision_value="on")
        state.readonly = _value_if_key_exists(properties, "readonly", "value", bool_comparision_value="on")

    return state
