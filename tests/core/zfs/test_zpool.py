import pytest
import json
from pathlib import Path
from unittest.mock import patch

from app.core.zfs.zpool import list_pool, get_pool_status, get_importable_pools, import_pool, export_pool, create_pool, destroy_pool, scrub_pool, _build_pool_state
from app.core.zfs.models import PoolState, ImportablePool, RaidType
from app.core.errors import ZFSCommandFailedError
from app.core.config import settings


def test_build_pool_state_from_list():
    test_dict = {
        'name': "fish",
        'properties': {
            'health': {'value': "ONLINE"},
            'size': {'value': "10000"},
            'allocated': {'value': "1000"},
            'free': {'value': "9000"},
        }
    }

    test_pool = PoolState(
        name="fish",
        health="ONLINE",
        size=10000,
        allocated=1000,
        free=9000
    )

    return_pool = _build_pool_state(test_dict)

    assert isinstance(return_pool, PoolState)
    assert return_pool == test_pool


def test_build_pool_state_from_status():
    """Verifies parsing a raw zpool status -j structure with a nested vdev tree."""
    status_dict = {
        "name": "tank",
        "state": "ONLINE",
        "vdevs": {
            "tank": {
                "name": "tank",
                "vdev_type": "root",
                "state": "ONLINE",
                "alloc_space": "1000",
                "total_space": "10000",
                "read_errors": "0",
                "write_errors": "0",
                "checksum_errors": "2",
                "vdevs": {
                    "raidz1-0": {
                        "name": "raidz1-0",
                        "vdev_type": "raidz",
                        "state": "ONLINE",
                        "alloc_space": "1000",
                        "total_space": "10000",
                        "read_errors": "0",
                        "write_errors": "0",
                        "checksum_errors": "2",
                        "vdevs": {
                            "sda": {
                                "name": "sda",
                                "vdev_type": "disk",
                                "state": "ONLINE",
                                "read_errors": "0",
                                "write_errors": "0",
                                "checksum_errors": "2"
                            }
                        }
                    }
                }
            }
        }
    }

    return_pool = _build_pool_state(status_dict)

    assert isinstance(return_pool, PoolState)
    assert return_pool.name == "tank"
    assert return_pool.health == "ONLINE"
    assert return_pool.size == 10000
    assert return_pool.allocated == 1000
    assert return_pool.free == 9000
    assert return_pool.checksum_errors == 2

    # Topology Assertions
    assert return_pool.vdev_tree is not None
    assert return_pool.vdev_tree.name == "tank"
    assert "raidz1-0" in return_pool.vdev_tree.vdevs
    
    raidz_vdev = return_pool.vdev_tree.vdevs["raidz1-0"]
    assert raidz_vdev.vdev_type == "raidz"
    assert "sda" in raidz_vdev.vdevs
    assert raidz_vdev.vdevs["sda"].checksum_errors == 2


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_list_pools(mock_run_command, load_cmd_json_fixture):
    mock_run_command.return_value = (0, load_cmd_json_fixture)

    zpools = await list_pool(uid="1000")

    mock_data = json.loads(load_cmd_json_fixture)
    assert len(zpools) == len(mock_data["pools"])
    for mock_pool in mock_data["pools"].values():
        assert _build_pool_state(mock_pool) in zpools


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_list_pool(mock_run_command, load_cmd_json_fixture):
    mock_run_command.return_value = (0, load_cmd_json_fixture)

    zpool = await list_pool(uid="1000", pool_name="tank")

    mock_data = json.loads(load_cmd_json_fixture)
    assert _build_pool_state(mock_data["pools"]["tank"]) == zpool


@pytest.mark.asyncio
@patch("app.core.zfs.zpool._build_pool_state")
@patch("app.core.zfs.zpool.execute_zfs_command_json")
async def test_list_pool(mock_execute, mock_build_state):
    mock_execute.return_value = {"pools": {"tank": {}}}
    mock_build_state.return_value = "mock_state"

    await list_pool(1000)
    mock_execute.assert_called_with(1000, [settings.ZPOOL_BINARY, "list", "-pj"])

    pool_name = "tank"
    await list_pool(1000, pool_name)
    mock_execute.assert_called_with(1000, [settings.ZPOOL_BINARY, "list", "-pj", pool_name], pool_name)


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_get_pool_status(mock_run_command, load_cmd_json_fixture):
    mock_run_command.return_value = (0, load_cmd_json_fixture)

    zpool = await get_pool_status(uid="1000", pool_name="tank")

    mock_data = json.loads(load_cmd_json_fixture)
    assert _build_pool_state(mock_data["pools"]["tank"]) == zpool


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_get_pool_statuss(mock_run_command, load_cmd_json_fixture):
    mock_run_command.return_value = (0, load_cmd_json_fixture)

    zpools = await get_pool_status(uid="1000")

    mock_data = json.loads(load_cmd_json_fixture)
    for pool in mock_data["pools"].values():
        assert _build_pool_state(pool) in zpools


@pytest.mark.asyncio
@patch("app.core.zfs.zpool._build_pool_state")
@patch("app.core.zfs.zpool.execute_zfs_command_json")
async def test_get_pool_status(mock_execute, mock_build_state):
    mock_execute.return_value = {"pools": {"tank": {}}}
    mock_build_state.return_value = "mock_state"

    await get_pool_status(1000)
    mock_execute.assert_called_with(1000, [settings.ZPOOL_BINARY, "status", "-pj"])

    pool_name = "tank"
    await get_pool_status(1000, pool_name)
    mock_execute.assert_called_with(1000, [settings.ZPOOL_BINARY, "status", "-pj", pool_name], pool_name)


@pytest.mark.asyncio
@patch("app.core.zfs.zpool.execute_zfs_command")
async def test_get_importable_pools(mock_execute, load_cmd_json_fixture):
    mock_execute.return_value = load_cmd_json_fixture

    await get_importable_pools(1000)
    mock_execute.assert_called_with(1000, [settings.ZPOOL_BINARY, "import"])


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_get_importable_pools(mock_run_command, load_cmd_json_fixture):
    mock_run_command.return_value = (0, load_cmd_json_fixture)

    importable_pools = await get_importable_pools(1000)

    assert importable_pools == [
        ImportablePool(name="fish", id=1123, healthy=True),
        ImportablePool(name="tank", id=1234, healthy=False)
    ]


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_get_importable_pools_no_id(mock_run_command, load_cmd_json_fixture, caplog):
    mock_run_command.return_value = (0, load_cmd_json_fixture)

    with pytest.raises(AttributeError) as e:
        await get_importable_pools(1000)

    assert "No id field in zpool import" in str(e.value)
    assert "No id field in zpool import" in caplog.text


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_get_importable_pools_char_id(mock_run_command, load_cmd_json_fixture, caplog):
    mock_run_command.return_value = (0, load_cmd_json_fixture)

    with pytest.raises(ValueError) as e:
        await get_importable_pools(1000)

    assert "Found non-int characters in pool id field:" in str(e.value)
    assert "Found non-int characters in pool id field:" in caplog.text


@pytest.mark.asyncio
@patch("app.core.zfs.zpool.execute_zfs_command") 
async def test_import_pool(mock_execute):
    pool_id = 4387097328
    
    assert await import_pool(1000, pool_id) is None
    mock_execute.assert_called_with(1000, [settings.ZPOOL_BINARY, "import", "4387097328"], pool_id)

    assert await import_pool(1000, pool_id, custom_name="new_tank") is None
    mock_execute.assert_called_with(1000, [settings.ZPOOL_BINARY, "import", "4387097328", "new_tank"], pool_id)


@pytest.mark.asyncio
@patch("app.core.zfs.zpool.execute_zfs_command") 
async def test_export_pool(mock_execute):
    pool_name = "tank"
    
    assert await export_pool(1000, pool_name) is None
    mock_execute.assert_called_with(1000, [settings.ZPOOL_BINARY, "export", pool_name], pool_name)


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
@pytest.mark.parametrize(
    "func, mock_output",
    [
        (list_pool, ""),
        (get_pool_status, '{"output_version":{"command":"zpool status"},"pools":{}}'),
        (get_importable_pools, "no pools available to import")
    ]
)
async def test_empty_pool_collections(mock_run_command, func, mock_output):
    mock_run_command.return_value = (0, mock_output)
    
    result = await func(uid="1000")
    
    assert result == []


@pytest.mark.asyncio
@patch("app.core.zfs.zpool.execute_zfs_command") 
async def test_create_pool(mock_execute):
    pool_name = "tank"
    disks = ["/dev/sda", "/dev/sdb", "/dev/sdc", "/dev/sdd"]
    
    for raid_type in list(RaidType):
        assert await create_pool(1000, pool_name, disks, raid_type) is None
        assert await create_pool(1000, pool_name, disks, raid_type, force=True) is None
    await create_pool(1000, pool_name, disks, RaidType.MIRROR)
    mock_execute.assert_called_with(1000, [settings.ZPOOL_BINARY, "create", '-o', 'ashift=12', '-O', 'compression=lz4', '-O', 'atime=off', pool_name, RaidType.MIRROR.value, "/dev/sda", "/dev/sdb", "/dev/sdc", "/dev/sdd"], pool_name)


@pytest.mark.asyncio
@patch("app.core.zfs.zpool.execute_zfs_command") 
async def test_destroy_pool(mock_execute):
    pool_name = "tank"
    
    assert await destroy_pool(1000, pool_name) is None
    mock_execute.assert_called_with(1000, [settings.ZPOOL_BINARY, "destroy", pool_name], pool_name)

    assert await destroy_pool(1000, pool_name, force=True) is None
    mock_execute.assert_called_with(1000, [settings.ZPOOL_BINARY, "destroy", "-f", pool_name], pool_name)


@pytest.mark.asyncio
@patch("app.core.zfs.zpool.execute_zfs_command") 
async def test_scrub_pool(mock_execute):
    pool_name = "tank"
    
    assert await scrub_pool(1000, pool_name) is None
    mock_execute.assert_called_with(1000, [settings.ZPOOL_BINARY, "scrub", pool_name], pool_name)