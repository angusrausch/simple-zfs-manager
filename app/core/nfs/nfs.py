from pathlib import Path

from app.core.config import settings
from app.core.system.file_mod import read_file, add_file_line, write_file
from app.core.nfs.models import NfsShare, NfsHost
from app.core.errors import NFSShareNotFoundError

async def read_shares(uid: int) -> list[NfsShare]:
    file_contents = read_file(settings.NFS_EXPORTS)

    lines = file_contents.splitlines()

    nfs_shares = []
    for line in lines:
        line = line.strip()
        if len(line) != 0 and line[0] != "#":
            nfs_shares.append(_create_nfs_model_from_str(line))
    
    return nfs_shares


async def add_share(uid: int, share_path: Path, hosts: list[str, list[str]]):
    share = _create_nfs_model(share_path, hosts)
    share_line = _create_nfs_shares_line(share)
    add_file_line(uid, settings.NFS_EXPORTS, share_line)


async def delete_share(uid: int, share: NfsShare):
    file_contents = read_file(settings.NFS_EXPORTS)
    lines = file_contents.splitlines()

    share_line_index = await _find_share_line(share, lines) 
    del lines[share_line_index]
    new_contents = "\n".join(lines) + "\n" if lines else ""
    write_file(uid, settings.NFS_EXPORTS, new_contents)


async def edit_share(uid: int, share: Share, new_share: Share):
    file_contents = read_file(settings.NFS_EXPORTS)
    lines = file_contents.splitlines()

    share_line_index = await _find_share_line(share, lines) 
    lines[share_line_index] = _create_nfs_shares_line(new_share)
    new_contents = "\n".join(lines) + "\n" if lines else ""
    write_file(uid, settings.NFS_EXPORTS, new_contents)


async def _find_share_line(share: NfsShare, lines: list[str]) -> int:
    for index, line in enumerate(lines):
        line = line.strip()
        if len(line) != 0 and line[0] != "#":
            if _create_nfs_model_from_str(line) == share:
                return index

    raise NFSShareNotFoundError.log_and_raise(f"No matching share found for \"{_create_nfs_shares_line(share)}\"")


def _create_nfs_shares_line(share: NfsShare):
    formatted_hosts = [f"{host.host}({",".join(host.options)})" for host in share.hosts]
    return f"{share.path} {" ".join(formatted_hosts)}"


def _create_nfs_model_from_str(line: str) -> NfsShare:
    path, hosts_str = line.split(maxsplit=1)

    host_list_str = hosts_str.split()

    host_list = []
    for host in host_list_str:
        hostname, options_str = host.split("(")
        
        options_str = options_str[0:-1]
        options = options_str.split(",")

        host_list.append([hostname, options])

    return _create_nfs_model(path, host_list)


def _create_nfs_model(share_path: Path, hosts: list[str, list[str]]) -> NfsShare:
    return NfsShare(
        path=share_path,
        hosts=[NfsHost(host=host[0], options=host[1]) for host in hosts]
    )

