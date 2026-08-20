import json
import logging

from app.core.system.runner import async_run_command
from app.core.zfs.models import PoolState

audit_logger = logging.getLogger("app.audit")


async def list_pools(uid) -> [PoolState]:
    command = ["zpool", "list", "-p", "-j"]
    status, zpool_json = await async_run_command(uid, command)

    if status == 127:
        audit_logger.error("[CMD] Command zpool not found, ensure `zfs` is installed")
        raise FileNotFoundError("Command zpool not found, ensure `zfs` is installed")
    elif status == 2:
        audit_logger.error("[CMD] Zpool appears to be different version. Arguments not parsing")
        raise AssertionError("Zpool appears to be different version. Arguments not parsing")
    elif status != 0:
        audit_logger.error(f"[CMD] {zpool_json}")
        raise Exception(zpool_json)

    if zpool_json == '':
        return []

    zpool_data = json.loads(zpool_json)

    pools = []
    for pool_raw_values in zpool_data["pools"].values():
        pools.append(
            _build_pool_state(pool_raw_values)
        )

    return pools

def _build_pool_state(pool_json: dict) -> PoolState:
    pool_properties = pool_json["properties"]
    return PoolState(
        name=pool_json["name"],
        health=pool_properties["health"]["value"],
        size=pool_properties["size"]["value"],
        allocated=pool_properties["allocated"]["value"],
        free=pool_properties["free"]["value"]
    )
