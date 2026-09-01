import logging
from configparser import ConfigParser
from pathlib import Path

from app.core.config import settings
from app.core.system.runner import async_run_command
from app.core.smb.models import SmbShare

audit_logger = logging.getLogger("app.audit")


async def list_shares(uid: int) -> list[SmbShare]:
    command = ["list"]

    return_str = await _execute_smb_command(uid, command)

    config = ConfigParser(interpolation=None)
    config.read_string(return_str)

    return [_build_smb_share(config[section]) for section in config.sections()]


async def get_share(uid: int, share_name: str) -> SmbShare:
    command = ["showshare", share_name]

    return_str = await _execute_smb_command(uid, command)

    config = ConfigParser(interpolation=None)
    config.read_string(return_str)

    return _build_smb_share(config[share_name])


def _build_smb_share(config: ConfigParser):
    return SmbShare(
        name = config.name,
        path = Path(config.get("path")) if config.get("path") else None,
        browsable = config.get("browseable") == "yes",
        read_only = config.get("read only") == "yes",
        public = config.get("public") == "yes",
        users = _build_smb_users(config.get("valid users")),
        force_user = config.get("force user"),
        create_mask = _build_permissions(config.get("create mask")),
        dir_mask = _build_permissions(config.get("directory mask")),
    )


def _build_permissions(mask_str: str) -> int:
    if not mask_str:
        return 0o660
    return int(mask_str, 8)


def _build_smb_users(users_str: str) -> list[str]:
    if not users_str:
        return []
    return [user.strip() for user in users_str.split(",")]


async def _execute_smb_command(uid: int, command_args: list[str], share_name: str | None = None) -> str:
    base_command = [settings.NET_BINARY, "conf"]
    full_command = base_command + command_args

    status, return_str = await async_run_command(uid, full_command)

    if status == 127:
        audit_logger.error(f"[CMD] Command `{full_command[0]}` not found, ensure it is installed")
        raise FileNotFoundError(f"Command `{full_command[0]}` not found, ensure it is installed")
    elif status in (126, 255):
        audit_logger.error(f"[CMD] Invalid Permissions: {return_str}")
        raise PermissionError(f"Invalid Permissions: {return_str}")
    elif status == 1:
        if share_name:
            if "SBC_ERR_NO_SUCH_SERVICE" in return_str:
                audit_logger.error(f"[CMD] Share does not exist: '{share_name}'")
                raise KeyError(f"Share does not exist: '{share_name}'")
        audit_logger.error(f"[CMD] An error occured: {return_str}")
        raise Exception(f"An error occured: {return_str}")

    return return_str