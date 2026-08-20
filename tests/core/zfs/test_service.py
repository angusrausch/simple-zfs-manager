import pytest
import json
from pathlib import Path
from unittest.mock import patch

from app.core.zfs.service import list_pools, list_pool, get_pool_status, get_pool_statuss, _build_pool_state
from app.core.zfs.models import PoolState

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

    assert type(return_pool) == PoolState
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
                "checksum_errors": "2",  # Test error bubble-up
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

    assert type(return_pool) == PoolState
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

    zpools = await list_pools(1000)

    mock_data = json.loads(load_cmd_json_fixture)
    for mock_pool in mock_data["pools"].values():
        assert _build_pool_state(mock_pool) in zpools

    assert len(mock_data["pools"]) == len(zpools)


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_list_pools_empty(mock_run_command):
    mock_run_command.return_value = (0, '')

    zpools = await list_pools(1000)

    assert zpools == []


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_list_pools_no_zfs(mock_run_command, caplog):
    mock_run_command.return_value = (127, 'System execution error: No such file or directory')

    with pytest.raises(FileNotFoundError) as e:
        zpools = await list_pools(1000)

    assert "[CMD] Command zpool not found, ensure `zfs` is installed" in caplog.text
    assert "Command zpool not found, ensure `zfs` is installed" in str(e.value)


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_list_pools_generic_error(mock_run_command, caplog):
    mock_run_command.return_value = (1, 'Generic Error')

    with pytest.raises(Exception) as e:
        zpools = await list_pools(1000)

    assert "[CMD] Generic Error" in caplog.text
    assert "Generic Error" in str(e.value)


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_list_pools_version_mismatch(mock_run_command, caplog):
    mock_run_command.return_value = (2, 'unrecognized command')

    with pytest.raises(AssertionError) as e:
        zpools = await list_pools(1000)

    assert "[CMD] Zpool appears to be different version. Arguments not parsing"
    assert "Zpool appears to be different version. Arguments not parsing" in str(e.value)


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_list_pool(mock_run_command, load_cmd_json_fixture):
    mock_run_command.return_value = (0, load_cmd_json_fixture)

    zpool = await list_pool(1000, "tank")

    mock_data = json.loads(load_cmd_json_fixture)
    assert _build_pool_state(mock_data["pools"]["tank"]) == zpool


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_list_pool_no_zfs(mock_run_command, caplog):
    mock_run_command.return_value = (127, 'System execution error: No such file or directory')

    with pytest.raises(FileNotFoundError) as e:
        zpools = await list_pool(1000, "tank")

    assert "[CMD] Command zpool not found, ensure `zfs` is installed" in caplog.text
    assert "Command zpool not found, ensure `zfs` is installed" in str(e.value)


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_list_pool_no_pool(mock_run_command, caplog):
    mock_run_command.return_value = (1, 'cannot open \'tank\': no such pool')

    with pytest.raises(FileNotFoundError) as e:
        zpools = await list_pool(1000, "tank")

    assert "[CMD] cannot open 'tank': no such pool" in caplog.text
    assert "cannot open 'tank': no such pool" in str(e.value)


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_list_pool_generic_error(mock_run_command, caplog):
    mock_run_command.return_value = (1, 'Generic Error')

    with pytest.raises(Exception) as e:
        zpools = await list_pool(1000, "tank")

    assert "[CMD] Generic Error" in caplog.text
    assert "Generic Error" in str(e.value)


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_list_pool_version_mismatch(mock_run_command, caplog):
    mock_run_command.return_value = (2, 'unrecognized command')

    with pytest.raises(AssertionError) as e:
        zpools = await list_pool(1000, "tank")

    assert "[CMD] Zpool appears to be different version. Arguments not parsing"
    assert "Zpool appears to be different version. Arguments not parsing" in str(e.value)


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_get_status(mock_run_command, load_cmd_json_fixture):
    mock_run_command.return_value = (0, load_cmd_json_fixture)

    zpool = await get_pool_status(1000, "tank")

    mock_data = json.loads(load_cmd_json_fixture)

    assert _build_pool_state(mock_data["pools"]["tank"]) == zpool


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_get_status_empty(mock_run_command, caplog):
    mock_run_command.return_value = (1, 'cannot open \'tank\': no such pool')

    with pytest.raises(FileNotFoundError) as e:
        zpools = await get_pool_status(1000, "tank")

    assert "[CMD] cannot open 'tank': no such pool" in caplog.text
    assert "cannot open 'tank': no such pool" in str(e.value)


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_get_status_no_zfs(mock_run_command, caplog):
    mock_run_command.return_value = (127, 'System execution error: No such file or directory')

    with pytest.raises(FileNotFoundError) as e:
        zpools = await get_pool_status(1000, "tank")

    assert "[CMD] Command zpool not found, ensure `zfs` is installed" in caplog.text
    assert "Command zpool not found, ensure `zfs` is installed" in str(e.value)


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_get_status_generic_error(mock_run_command, caplog):
    mock_run_command.return_value = (1, 'Generic Error')

    with pytest.raises(Exception) as e:
        zpools = await get_pool_status(1000, "tank")

    assert "[CMD] Generic Error" in caplog.text
    assert "Generic Error" in str(e.value)


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_get_status_version_mismatch(mock_run_command, caplog):
    mock_run_command.return_value = (2, 'unrecognized command')

    with pytest.raises(AssertionError) as e:
        zpools = await get_pool_status(1000, "tank")

    assert "[CMD] Zpool appears to be different version. Arguments not parsing"
    assert "Zpool appears to be different version. Arguments not parsing" in str(e.value)


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_get_statuss(mock_run_command, load_cmd_json_fixture):
    mock_run_command.return_value = (0, load_cmd_json_fixture)

    zpools = await get_pool_statuss(1000)
    print(zpools)
    mock_data = json.loads(load_cmd_json_fixture)
    for pool in mock_data["pools"].values():
        print("------")
        print(_build_pool_state(pool))
        assert _build_pool_state(pool) in zpools


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_get_statuss_empty(mock_run_command, caplog):
    mock_run_command.return_value = (0, '{"output_version":{"command":"zpool status"},"pools":{}}')

    zpools = await get_pool_statuss(1000)

    assert len(zpools) == 0


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_get_statuss_no_zfs(mock_run_command, caplog):
    mock_run_command.return_value = (127, 'System execution error: No such file or directory')

    with pytest.raises(FileNotFoundError) as e:
        zpools = await get_pool_statuss(1000)

    assert "[CMD] Command zpool not found, ensure `zfs` is installed" in caplog.text
    assert "Command zpool not found, ensure `zfs` is installed" in str(e.value)


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_get_statuss_generic_error(mock_run_command, caplog):
    mock_run_command.return_value = (1, 'Generic Error')

    with pytest.raises(Exception) as e:
        zpools = await get_pool_statuss(1000)

    assert "[CMD] Generic Error" in caplog.text
    assert "Generic Error" in str(e.value)


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_get_statuss_version_mismatch(mock_run_command, caplog):
    mock_run_command.return_value = (2, 'unrecognized command')

    with pytest.raises(AssertionError) as e:
        zpools = await get_pool_statuss(1000)

    assert "[CMD] Zpool appears to be different version. Arguments not parsing"
    assert "Zpool appears to be different version. Arguments not parsing" in str(e.value)

