import logging
from configparser import ConfigParser
from pathlib import Path

from app.core.config import settings
from app.core.system.runner import async_run_command
from app.core.smb.models import SmbShare
from app.utils.sanitise import sanitise_path

audit_logger = logging.getLogger("app.audit")


async def list_shares(uid: int) -> list[SmbShare]:
    command = ["list"]

    return_str = await _execute_smb_command(uid, command)

    config = ConfigParser(interpolation=None)
    config.read_string(return_str)

    return [_build_smb_share(config[section]) for section in config.sections()]


async def get_share(uid: int, share_name: str) -> SmbShare:
    command = ["showshare", share_name]

    return_str = await _execute_smb_command(uid, command, share_name)

    config = ConfigParser(interpolation=None)
    config.read_string(return_str)

    return _build_smb_share(config[share_name])


async def create_share(uid: int, share_name: str, share_path: Path, writeable: bool = False, guest_ok: bool = False):
    writeable_param = "writeable=y" if writeable else "writeable=n"
    guest_ok_param = "guest_ok=y" if guest_ok else "guest_ok=n"
    safe_path = sanitise_path(share_path)
    
    command = ["addshare", share_name, str(safe_path), writeable_param, guest_ok_param]

    await _execute_smb_command(uid, command, share_name)


async def add_share_user(uid: int, share_name: str, users: str | list[str]):
    current_users = _build_smb_users(await _get_param(uid, share_name, "valid users"))

    if type(users) == str:
        users = [users]
    for user in users:
        if user in current_users:
            audit_logger.error(f"[SMB] Attempted to add user \'{user}\' to `{share_name}` but user already present")
            raise ValueError(f"User \'{user}\' already present in share")
        current_users.append(user)
    
    users_str = ", ".join(current_users)
    await _set_param(uid, share_name, "valid users", users_str)


async def del_share_user(uid: int, share_name: str, users: str):
    current_users = _build_smb_users(await _get_param(uid, share_name, "valid users"))

    if type(users) == str:
        users = [users]
    
    try:
        for user in users:
            current_users.remove(user)
    except ValueError:
        audit_logger.error(f"[SMB] Attempted to delete user \'{user}\' from `{share_name}` but user not present")
        raise ValueError(f"User \'{user}\' not present in `{share_name}`")

    users_str = ", ".join(current_users)
    await _set_param(uid, share_name, "valid users", users_str)


async def set_share_read_only(uid: int, share_name: str, value: bool):
    if value:
        await _set_param(uid, share_name, "read only", "yes")
    else:
        await _set_param(uid, share_name, "read only", "no")


async def get_share_read_only(uid: int, share_name: str) -> bool:
    read_only = await _get_param(uid, share_name, "read only")
    return not read_only == "no"


async def set_share_guest_ok(uid: int, share_name: str, value: bool):
    if value:
        await _set_param(uid, share_name, "guest ok", "yes")
    else:
        await _set_param(uid, share_name, "guest ok", "no")


async def get_share_guest_ok(uid: int, share_name: str) -> bool:
    guest_ok = await _get_param(uid, share_name, "guest ok")
    return guest_ok == "yes"


async def set_share_browseable(uid: int, share_name: str, value: bool):
    if value:
        await _set_param(uid, share_name, "browseable", "yes")
    else:
        await _set_param(uid, share_name, "browseable", "no")


async def get_share_browseable(uid: int, share_name: str) -> bool:
    browsable = await _get_param(uid, share_name, "browseable")
    return not browsable == "no"


async def get_share_path(uid: int, share_name: str) -> Path:
    return Path(await _get_param(uid, share_name, "path"))


async def set_share_path(uid: int, share_name: str, path: Path):
    path = sanitise_path(path)
    if not path.exists():
        raise ValueError("Path does not exist. Please choose a different path or create this path and try again")

    await _set_param(uid, share_name, "path", str(path))


async def _get_param(uid: int, share_name: str, param_str:str) -> str:
    command = ["getparm", share_name, param_str]

    return await _execute_smb_command(uid, command, share_name)


async def _set_param(uid: int, share_name: str, param_str: str, param_value_str: str):
    command = ["setparm", share_name, param_str, param_value_str]

    await _execute_smb_command(uid, command, share_name)


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


async def _execute_smb_command(uid: int, command_args: list[str], share_name: str | None = None) -> str | None:
    base_command = [settings.NET_BINARY, "conf"]
    full_command = base_command + command_args

    status, return_str = await async_run_command(uid, full_command)

    if status == 127:
        audit_logger.error(f"[CMD] Command `{full_command[0]}` not found, ensure it is installed")
        raise FileNotFoundError(f"Command `{full_command[0]}` not found, ensure it is installed")
    elif status == 126:
        audit_logger.error(f"[CMD] Invalid Permissions: {return_str}")
        raise PermissionError(f"Invalid Permissions: {return_str}")
    elif status != 0:
        if "WERR_ACCESS_DENIED" in return_str:
            audit_logger.error(f"[CMD] Invalid Permissions: {return_str}")
            raise PermissionError(f"Invalid Permissions: {return_str}")
        if share_name:
            if "SBC_ERR_NO_SUCH_SERVICE" in return_str:
                audit_logger.error(f"[CMD] Share does not exist: '{share_name}'")
                raise KeyError(f"Share does not exist: '{share_name}'")
            if "Error: given parameter '" in return_str and "' is not set." in return_str:
                return None
        audit_logger.error(f"[CMD] An error occured: {return_str}")
        raise Exception(f"An error occured: {return_str}")

    return return_str