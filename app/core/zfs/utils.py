import asyncio
import json
import logging
import re
import os

from app.core.errors import ZFSCommandFailedError
from app.core.system.runner import async_run_command, create_piped_asyncio_subprocess

audit_logger = logging.getLogger("app.audit")


async def execute_zfs_command_json(uid: int, command: list[str], pool_name: str | None = None) -> dict:
    returned_string = await execute_zfs_command(uid, command, pool_name)
    if not returned_string.strip() or "no datasets available" in returned_string:
        return {}

    return json.loads(returned_string)


async def execute_zfs_command(uid: int, command: list[str], pool_name: str | None = None, new_name: str | None = None) -> str:
    status, returned_string = await async_run_command(uid, command)

    _parse_zfs_error(status, returned_string, pool_name, new_name)

    return returned_string


async def execute_zfs_replication(uid: int, send_command: list[str], recv_command: list[str], snapshot: str | None = None, target: str | None = None):
    read_fd, write_fd = os.pipe()

    try:
        send_proc = await asyncio.create_subprocess_exec(
            *send_command,
            stdin=asyncio.subprocess.PIPE,
            stdout=write_fd,
            stderr=asyncio.subprocess.PIPE
        )

        recv_proc = await asyncio.create_subprocess_exec(
            *recv_command,
            stdin=read_fd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

    finally:
        os.close(read_fd)
        os.close(write_fd)

    _, send_stderr = await send_proc.communicate()
    _, recv_stderr = await recv_proc.communicate()

    target_parent = "/".join(target.split("/")[0:-1])

    if send_proc.returncode != 0:
        _parse_zfs_error(send_proc.returncode, send_stderr.decode(), snapshot, target_parent)
        
    if recv_proc.returncode != 0:
        _parse_zfs_error(recv_proc.returncode, recv_stderr.decode(), snapshot, target_parent)


def _parse_zfs_error(status: int, returned_string: str, pool_name: str | None = None, new_name: str | None = None):
    if status == 127:
        audit_logger.error("[CMD] Command zpool not found, ensure `zfs` is installed")
        raise FileNotFoundError("Command zpool not found, ensure `zfs` is installed")
    elif status == 2:
        audit_logger.error("[CMD] Zpool appears to be different version. Arguments not parsing")
        raise AssertionError("Zpool appears to be different version. Arguments not parsing")
    elif status != 0:
        if pool_name and (f"'{pool_name}': no such pool" in returned_string or 
                f"'{pool_name}': dataset does not exist" in returned_string or
                f"'{new_name}': dataset does not exist" in returned_string or
                f"'{new_name}': missing dataset name" in returned_string):
            audit_logger.error(f"[CMD] {returned_string}")
            raise FileNotFoundError(returned_string)
        if "parent does not exist" in returned_string:
            error_message = f"[CMD] The following Error occured, Use create parents option to override:\n\'{returned_string}\'"
            audit_logger.error(error_message)
            raise FileNotFoundError(error_message)
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
        if (pool_name and re.search(rf"cannot rollback to '{re.escape(pool_name)}@.*?': more recent snapshots or bookmarks exist", returned_string) and 
                "use '-r' to force deletion of the following snapshots and bookmarks:" in returned_string):
            error_details = returned_string.split("use '-r' to force deletion of the following snapshots and bookmarks:")[1].strip()
            raise ZFSCommandFailedError(f"Cannot restore to snapshot where snapshots exist between target and current, use the destructive option to delete these snapshots.\nThe following snapshots are required to be removed:\n{error_details}")
        raise ZFSCommandFailedError.log_and_raise(returned_string)