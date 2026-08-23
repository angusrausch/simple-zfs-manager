
import json
import logging

from app.core.errors import ZFSCommandFailedError
from app.core.system.runner import async_run_command

audit_logger = logging.getLogger("app.audit")


async def execute_zfs_command_json(uid: int, command: list[str], pool_name: str | None = None) -> dict:
    returned_string = await execute_zfs_command(uid, command, pool_name)
    if not returned_string.strip() or "no datasets available" in returned_string:
        return {}

    return json.loads(returned_string)


async def execute_zfs_command(uid: int, command: list[str], pool_name: str | None = None) -> str:
    status, returned_string = await async_run_command(uid, command)

    if status == 127:
        audit_logger.error("[CMD] Command zpool not found, ensure `zfs` is installed")
        raise FileNotFoundError("Command zpool not found, ensure `zfs` is installed")
    elif status == 2:
        audit_logger.error("[CMD] Zpool appears to be different version. Arguments not parsing")
        raise AssertionError("Zpool appears to be different version. Arguments not parsing")
    elif status != 0:
        if pool_name and (f"'{pool_name}': no such pool" in returned_string or 
                f"'{pool_name}': dataset does not exist" in returned_string):
            audit_logger.error(f"[CMD] {returned_string}")
            raise FileNotFoundError(returned_string)
        if "invalid vdev specification" in returned_string:
            if "use '-f' to override the following errors:" in returned_string:
                error_details = returned_string.split("use '-f' to override the following errors:")[1].strip()
                raise ZFSCommandFailedError(f"The following Error occured, Use force option to override:\n\'{error_details}\'")
            error_mapping = {
                "mirror requires at least 2 devices": "Not enough disks selected for Mirror, must use at least 2 disks",
                "raidz1 requires at least 2 devices": "Not enough disks selected for RAIDZ1, must use at least 2 disks",
                "raidz2 requires at least 3 devices": "Not enough disks selected for RAIDZ2, must use at least 3 disks",
                "raidz3 requires at least 4 devices": "Not enough disks selected for RAIDZ3, must use at least 4 disks",
            }
            for substring, custom_message in error_mapping.items():
                if substring in returned_string:
                    raise ZFSCommandFailedError(custom_message)
        raise ZFSCommandFailedError.log_and_raise(returned_string)

    return returned_string
