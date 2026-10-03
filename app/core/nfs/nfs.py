from pathlib import Path

from app.core.config import settings
from app.core.system.file_mod import read_file, write_file
from app.core.nfs.models import NfsShare, NfsHost

async def read_shares(uid: int) -> list[NfsShare]:
    file_contents = read_file(settings.NFS_EXPORTS)

    lines = file_contents.splitlines()

    nfs_shares = []
    for line in lines:
        line = line.strip()
        if line[0] != "#" and len(line) != 0:
            nfs_shares.append(_create_nfs_model(line))


def _create_nfs_shares_line(share_path: Path, hosts: list[(str, list[str])]):
    formatted_hosts = []
    for host in hosts:
        hostname = host[0]
        options = host[1]
        formatted_hosts.append(
                f"{hostname}({",".join(options)})"
            )

    return f"{share_path} {" ".join(formatted_hosts)}"


def _create_nfs_model(line: str) -> NfsShare:
    path, hosts_str = line.split(maxsplit=1)

    host_list_str = hosts_str.split()

    host_list = []
    for host in host_list_str:
        hostname, options_str = host.split("(")
        
        options_str = options_str[0:-1]
        options = options_str.split(",")

        host_list.append(
            NfsHost(
                host=hostname,
                options=options
            )
        )

    return NfsShare(
        path=path,
        hosts=host_list
    )

