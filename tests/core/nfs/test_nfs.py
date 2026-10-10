import pytest
from pathlib import Path

from app.core.nfs.nfs import _create_nfs_shares_line, _create_nfs_model, add_share, read_shares
from app.core.nfs.models import NfsShare, NfsHost
from app.core.config import settings


@pytest.mark.parametrize(
    "path, hosts, expected_line",
    [
        ("/tank/turret", [("10.0.0.1", ["rw", "sync", "no_subtree_check"])], "/tank/turret 10.0.0.1(rw,sync,no_subtree_check)"),
        ("/tank/track", [("10.0.0.0/24", ["ro", "sync", "no_subtree_check"])], "/tank/track 10.0.0.0/24(ro,sync,no_subtree_check)"),
        ("/tanks/shell", [("10.0.0.1", ["ro", "sync", "no_subtree_check"]), 
                        ("10.0.0.10", ["rw", "sync", "no_subtree_check"])],
                        "/tanks/shell 10.0.0.1(ro,sync,no_subtree_check) 10.0.0.10(rw,sync,no_subtree_check)")
    ]
)
def test_create_nfs_share_line(path, hosts, expected_line):
    assert _create_nfs_shares_line(path, hosts) == expected_line


@pytest.mark.parametrize(
    "input_line, path, hosts",
    [
        ("/tank/turret 10.0.0.1(rw,sync,no_subtree_check)", Path("/tank/turret"), [("10.0.0.1", ["rw", "sync", "no_subtree_check"])]),
        ("/tank/track 10.0.0.0/24(ro,sync,no_subtree_check)", Path("/tank/track"), [("10.0.0.0/24", ["ro", "sync", "no_subtree_check"])]),
        ("/tanks/shell 10.0.0.1(ro,sync,no_subtree_check) 10.0.0.10(rw,sync,no_subtree_check)",
            Path("/tanks/shell"), [("10.0.0.1", ["ro", "sync", "no_subtree_check"]), 
                        ("10.0.0.10", ["rw", "sync", "no_subtree_check"])])
    ]
)
def test_create_nfs_model(input_line, path, hosts):
    model = _create_nfs_model(input_line)

    assert model.path == path
    for host in hosts:
        assert NfsHost(host=host[0], options=host[1]) in model.hosts


@pytest.mark.asyncio
async def test_add_share(create_nfs_export_file):
    # assert open(settings.NFS_EXPORTS).read() == ""

    share_path = Path("/mnt/share")
    hosts = [("10.0.0.1", ["ro", "sync", "no_subtree_check"]), ("10.0.0.10", ["rw", "sync", "no_subtree_check"])]

    share_line = _create_nfs_shares_line(share_path, hosts)
    
    await add_share(1000, share_path, hosts)
    assert open(settings.NFS_EXPORTS).read() == "\n" + share_line

    await add_share(1000, share_path, hosts)
    assert open(settings.NFS_EXPORTS).read() == "\n" + share_line + "\n" + share_line


@pytest.mark.asyncio
async def test_read_shares(create_nfs_export_file):
    contents = """
# Comment
/tank/turret 10.0.0.1(rw,sync,no_subtree_check)
/tank/track 10.0.0.0/24(ro,sync,no_subtree_check)
# Another Comment
/tanks/shell 10.0.0.1(ro,sync,no_subtree_check) 10.0.0.10(rw,sync,no_subtree_check)
        """
    open(settings.NFS_EXPORTS, 'w').write(contents)

    shares = await read_shares(1000)

    expected_shares = [
            _create_nfs_model("/tank/turret 10.0.0.1(rw,sync,no_subtree_check)"),
            _create_nfs_model("/tank/track 10.0.0.0/24(ro,sync,no_subtree_check)"),
            _create_nfs_model("/tanks/shell 10.0.0.1(ro,sync,no_subtree_check) 10.0.0.10(rw,sync,no_subtree_check)")
        ]

    assert shares == expected_shares