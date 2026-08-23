import json
import logging

from app.core.zfs.utils import execute_zfs_command
from app.core.zfs.models import PoolState, VDevNode, ImportablePool, RaidType
from app.core.config import settings
from app.core.errors import ZFSCommandFailedError

audit_logger = logging.getLogger("app.audit")


async def create_dataset(uid: int, parent: str, dataset_name: str):
    full_dataset_name = parent + "/" + dataset_name
    command = [settings.ZFS_BINARY, "create", full_dataset_name]

    await execute_zfs_command(uid, command, full_dataset_name)


async def destroy_dataset(uid: int, dataset_name: str):
    command = [settings.ZFS_BINARY, "destroy", dataset_name]

    await execute_zfs_command(uid, command, dataset_name)