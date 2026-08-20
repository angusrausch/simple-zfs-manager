import json
import logging

from app.core.system.runner import async_run_command
from app.core.zfs.models import PoolState, VDevNode
from app.core.config import settings

audit_logger = logging.getLogger("app.audit")


async def list_pool(uid: int, pool_name: str) -> PoolState:
    command = [settings.ZPOOL_BINARY, "list", "-pj", pool_name]
    zpool_data = await _execute_zpool_command_json(uid, command, pool_name)
    return _build_pool_state(zpool_data["pools"][pool_name])


async def list_pools(uid: int) -> list[PoolState]:
    command = [settings.ZPOOL_BINARY, "list", "-pj"]
    zpool_data = await _execute_zpool_command_json(uid, command)
    
    if not zpool_data or "pools" not in zpool_data:
        return []

    return [_build_pool_state(raw) for raw in zpool_data["pools"].values()]


async def get_pool_status(uid: int, pool_name: str) -> PoolState:
    command = [settings.ZPOOL_BINARY, "status", "-pj", pool_name]
    zpool_data = await _execute_zpool_command_json(uid, command, pool_name)
    return _build_pool_state(zpool_data["pools"][pool_name])


async def get_pool_statuss(uid: int) -> list[PoolState]:
    command = [settings.ZPOOL_BINARY, "status", "-pj"]
    zpool_data = await _execute_zpool_command_json(uid, command)

    if not zpool_data or "pools" not in zpool_data or len(zpool_data["pools"]) == 0:
        return []

    return [_build_pool_state(raw) for raw in zpool_data["pools"].values()]


async def _execute_zpool_command_json(uid: int, command: list[str], pool_name: str | None = None) -> dict:
    returned_string = await _execute_zpool_command(uid, command, pool_name)
    if not returned_string.strip():
        return {}

    return json.loads(returned_string)


async def _execute_zpool_command(uid: int, command: list[str], pool_name: str | None = None) -> str:
    """Executes a zpool command, handles standard exit statuses, and returns the JSON payload."""
    status, returned_string = await async_run_command(uid, command)

    if status == 127:
        audit_logger.error("[CMD] Command zpool not found, ensure `zfs` is installed")
        raise FileNotFoundError("Command zpool not found, ensure `zfs` is installed")
    elif status == 2:
        audit_logger.error("[CMD] Zpool appears to be different version. Arguments not parsing")
        raise AssertionError("Zpool appears to be different version. Arguments not parsing")
    elif status != 0:
        audit_logger.error(f"[CMD] {returned_string}")
        if pool_name and returned_string == f"cannot open '{pool_name}': no such pool":
            raise FileNotFoundError(returned_string)
        raise Exception(returned_string)

    return returned_string


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