import json
import logging
import re

from app.core.zfs.utils import execute_zfs_command, execute_zfs_command_json
from app.core.zfs.models import PoolState, VDevNode, ImportablePool, RaidType
from app.core.config import settings
from app.core.errors import ZFSCommandFailedError

audit_logger = logging.getLogger("app.audit")


async def list_pool(uid: int, pool_name: str) -> PoolState:
    command = [settings.ZPOOL_BINARY, "list", "-pj", pool_name]
    zpool_data = await execute_zfs_command_json(uid, command, pool_name)
    return _build_pool_state(zpool_data["pools"][pool_name])


async def list_pools(uid: int) -> list[PoolState]:
    command = [settings.ZPOOL_BINARY, "list", "-pj"]
    zpool_data = await execute_zfs_command_json(uid, command)
    
    if not zpool_data or "pools" not in zpool_data:
        return []

    return [_build_pool_state(raw) for raw in zpool_data["pools"].values()]


async def get_pool_status(uid: int, pool_name: str) -> PoolState:
    command = [settings.ZPOOL_BINARY, "status", "-pj", pool_name]
    zpool_data = await execute_zfs_command_json(uid, command, pool_name)
    return _build_pool_state(zpool_data["pools"][pool_name])


async def get_pool_statuss(uid: int) -> list[PoolState]:
    command = [settings.ZPOOL_BINARY, "status", "-pj"]
    zpool_data = await execute_zfs_command_json(uid, command)

    if not zpool_data or "pools" not in zpool_data or len(zpool_data["pools"]) == 0:
        return []

    return [_build_pool_state(raw) for raw in zpool_data["pools"].values()]


async def get_importable_pools(uid: int) -> list[ImportablePool]:
    command = [settings.ZPOOL_BINARY, "import"]
    returned_string = await execute_zfs_command(uid, command)
    
    if returned_string == "no pools available to import":
        return []

    importable_pools = []
    for pool in returned_string.split("pool: ")[1:]:
        lines = pool.splitlines()
        name = lines[0].strip()
        id_match = re.search(r"id:\s*(\w+)", pool)
        try:
            if id_match.group(1):
                try:
                    pool_id = int(id_match.group(1))
                except ValueError:
                    audit_logger.error(f"[CMD] Found non-int characters in pool id field: {pool}")
                    raise ValueError(f"Found non-int characters in pool id field: {pool}")
        except AttributeError:
            audit_logger.error(f"[CMD] No id field in zpool import: {pool}")
            raise AttributeError("No id field in zpool import")
        health_match = re.search(r"state:\s*(\w+)", pool)
        is_online = (health_match.group(1) == "ONLINE") if health_match else False
        importable_pools.append(ImportablePool(
            name=name,
            id=pool_id,
            healthy=is_online
        ))
    
    return importable_pools


async def import_pool(uid: int, id: int, custom_name: str = None):
    if custom_name:
        command = [settings.ZPOOL_BINARY, "import", str(id), custom_name]
    else:
        command = [settings.ZPOOL_BINARY, "import", str(id)]
    
    await execute_zfs_command(uid, command, id)


async def export_pool(uid: int, name: str):
    command = [settings.ZPOOL_BINARY, "export", name]
    await execute_zfs_command(uid, command, name)


async def create_pool(uid: int, name: str, disks: list[str], raid_type: RaidType, force: bool = False):
    command = [
        settings.ZPOOL_BINARY,
        "create",
        "-o", "ashift=12",
        "-O", "compression=lz4",
        "-O", "atime=off",
    ]
    if force:
        command.append("-f")
    command.append(name)
    if raid_type != RaidType.STRIPE:
        command.append(raid_type.value)
    command += disks
    
    await execute_zfs_command(uid, command, name)


async def destroy_pool(uid:int, pool_name: str, force: bool = False):
    command = [settings.ZPOOL_BINARY, "destroy", "-f", pool_name] if force else [settings.ZPOOL_BINARY, "destroy", pool_name]

    await execute_zfs_command(uid, command, pool_name)


async def scrub_pool(uid: int, pool_name: str):
    command = [settings.ZPOOL_BINARY, "scrub", pool_name]
    await execute_zfs_command(uid, command, pool_name)


def _parse_vdev_tree(vdev_name: str, vdev_data: dict) -> VDevNode:
    """Helper to recursively parse the nested vdev JSON tree."""
    child_vdevs = None
    if "vdevs" in vdev_data and isinstance(vdev_data["vdevs"], dict):
        child_vdevs = {
            k: _parse_vdev_tree(k, v) for k, v in vdev_data["vdevs"].items()
        }
        
    return VDevNode(
        name=vdev_name,
        vdev_type=vdev_data.get("vdev_type", "unknown"),
        state=vdev_data.get("state", "UNKNOWN"),
        path=vdev_data.get("path"),
        read_errors=int(vdev_data.get("read_errors", 0)),
        write_errors=int(vdev_data.get("write_errors", 0)),
        checksum_errors=int(vdev_data.get("checksum_errors", 0)),
        vdevs=child_vdevs
    )


def _build_pool_state(data: dict) -> PoolState:
    if "properties" in data: # List
        properties = data["properties"]
        return PoolState(
            name=data["name"],
            health=properties["health"]["value"],
            size=int(properties["size"]["value"]),
            allocated=int(properties["allocated"]["value"]),
            free=int(properties["free"]["value"]),
        )
    else: # Status
        root_vdev_name = data["name"]
        root_vdev = data.get("vdevs", {}).get(root_vdev_name, {})
        
        vdev_tree = None
        if root_vdev:
            vdev_tree = _parse_vdev_tree(root_vdev_name, root_vdev)
            
        return PoolState(
            name=data["name"],
            health=data["state"],
            size=int(root_vdev.get("total_space", 0)),
            allocated=int(root_vdev.get("alloc_space", 0)),
            free=int(root_vdev.get("free_space", 0)) if "free_space" in root_vdev else int(root_vdev.get("total_space", 0)) - int(root_vdev.get("alloc_space", 0)),
            read_errors=int(root_vdev.get("read_errors", 0)),
            write_errors=int(root_vdev.get("write_errors", 0)),
            checksum_errors=int(root_vdev.get("checksum_errors", 0)),
            vdev_tree=vdev_tree
        )