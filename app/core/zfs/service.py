import json
import logging

from app.core.system.runner import async_run_command
from app.core.zfs.models import PoolState, VDevNode
from app.core.config import settings

audit_logger = logging.getLogger("app.audit")


async def list_pool(uid: str, pool_name: str) -> [PoolState]:
    command = [settings.ZPOOL_BINARY, "list", "-pj", pool_name]
    status, returned_string = await async_run_command(uid, command)

    if status == 127:
        audit_logger.error("[CMD] Command zpool not found, ensure `zfs` is installed")
        raise FileNotFoundError("Command zpool not found, ensure `zfs` is installed")
    elif status == 2:
        audit_logger.error("[CMD] Zpool appears to be different version. Arguments not parsing")
        raise AssertionError("Zpool appears to be different version. Arguments not parsing")
    elif status != 0:
        audit_logger.error(f"[CMD] {returned_string}")
        if returned_string == f"cannot open \'{pool_name}\': no such pool":
            raise FileNotFoundError(returned_string)
        else:
            raise Exception(returned_string)

    zpool_data = json.loads(returned_string)

    return _build_pool_state(zpool_data["pools"][pool_name])


async def list_pools(uid: str) -> [PoolState]:
    command = [settings.ZPOOL_BINARY, "list", "-pj"]
    status, returned_string = await async_run_command(uid, command)

    if status == 127:
        audit_logger.error("[CMD] Command zpool not found, ensure `zfs` is installed")
        raise FileNotFoundError("Command zpool not found, ensure `zfs` is installed")
    elif status == 2:
        audit_logger.error("[CMD] Zpool appears to be different version. Arguments not parsing")
        raise AssertionError("Zpool appears to be different version. Arguments not parsing")
    elif status != 0:
        audit_logger.error(f"[CMD] {returned_string}")
        raise Exception(returned_string)

    if returned_string == '':
        return []

    zpool_data = json.loads(returned_string)

    pools = []
    for pool_raw_values in zpool_data["pools"].values():
        pools.append(
            _build_pool_state(pool_raw_values)
        )

    return pools


async def get_pool_status(uid: str, pool_name: str) -> PoolState:
    command = [settings.ZPOOL_BINARY, "status", "-pj", pool_name]
    status, returned_string = await async_run_command(uid, command)

    if status == 127:
        audit_logger.error("[CMD] Command zpool not found, ensure `zfs` is installed")
        raise FileNotFoundError("Command zpool not found, ensure `zfs` is installed")
    elif status == 2:
        audit_logger.error("[CMD] Zpool appears to be different version. Arguments not parsing")
        raise AssertionError("Zpool appears to be different version. Arguments not parsing")
    elif status != 0:
        audit_logger.error(f"[CMD] {returned_string}")
        if returned_string == f"cannot open \'{pool_name}\': no such pool":
            raise FileNotFoundError(returned_string)
        else:
            raise Exception(returned_string)

    zpool_data = json.loads(returned_string)

    return _build_pool_state(zpool_data["pools"][pool_name])


async def get_pool_statuss(uid: str) -> PoolState:
    command = [settings.ZPOOL_BINARY, "status", "-pj"]
    status, returned_string = await async_run_command(uid, command)

    if status == 127:
        audit_logger.error("[CMD] Command zpool not found, ensure `zfs` is installed")
        raise FileNotFoundError("Command zpool not found, ensure `zfs` is installed")
    elif status == 2:
        audit_logger.error("[CMD] Zpool appears to be different version. Arguments not parsing")
        raise AssertionError("Zpool appears to be different version. Arguments not parsing")
    elif status != 0:
        audit_logger.error(f"[CMD] {returned_string}")
        raise Exception(returned_string)

    zpool_data = json.loads(returned_string)

    if len(zpool_data["pools"]) == 0:
        return []

    pools = []
    for pool_raw_values in zpool_data["pools"].values():
        pools.append(
            _build_pool_state(pool_raw_values)
        )
    
    return pools


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