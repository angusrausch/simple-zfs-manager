import json

from app.core.system.runner import run_command
from app.core.zfs.zpool import get_used_disks


def list_disks(uid: int) -> list[dict]:
    def _is_mounted(disk):
        return disk["mountpoint"] is not None or any(
            child["mountpoint"] is not None for child in disk.get("children", [])
        )

    return [
        {
            'name': disk['name'],
            'size': disk['size'],
            'mounted': _is_mounted(disk)
        } 
        for disk in _get_disk_json(uid)
    ]


async def list_unused_disks(uid: int) -> list[dict]:
    used_disks = await get_used_disks(uid)
    return [disk for disk in list_disks(uid) if not disk["mounted"] and disk["name"] not in used_disks]


def _get_disk_json(uid: int) -> dict:
    command = ["lsblk", "-b", "--json", "-o", "name,size,mountpoint"]

    status, return_str = run_command(uid, command)

    if status != 0:
        raise Exception(return_str)

    return json.loads(return_str)["blockdevices"]
