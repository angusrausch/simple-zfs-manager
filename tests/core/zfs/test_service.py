import pytest
import json
from pathlib import Path
from unittest.mock import patch

from app.core.zfs.service import list_pools, list_pool, get_pool_status, get_pool_statuss, get_importable_pools, import_pool, _build_pool_state, _execute_zpool_command
from app.core.zfs.models import PoolState, ImportablePools


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
@pytest.mark.parametrize(
    "exit_status, output, expected_exception, error_msg",
    [
        (127, "Error...", FileNotFoundError, "Command zpool not found, ensure `zfs` is installed"),
        (2, "Error...", AssertionError, "Zpool appears to be different version. Arguments not parsing"),
        (1, "Generic Error", Exception, "Generic Error"),
    ]
)
async def test_execute_zpool_command_errors(mock_run, exit_status, output, expected_exception, error_msg, caplog):
    mock_run.return_value = (exit_status, output)
    
    with pytest.raises(expected_exception) as e:
        await _execute_zpool_command(uid="1000", command=["zpool", "list"])
        
    assert error_msg in caplog.text
    assert error_msg in str(e.value)


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_execute_zpool_command_missing_pool(mock_run, caplog):
    mock_run.return_value = (1, "cannot open 'tank': no such pool")
    
    with pytest.raises(FileNotFoundError) as e:
        await _execute_zpool_command(uid="1000", command=["zpool", "list", "tank"], pool_name="tank")
        
    assert "[CMD] cannot open 'tank': no such pool" in caplog.text
    assert "cannot open 'tank': no such pool" in str(e.value)


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_list_pools(mock_run_command, load_cmd_json_fixture):
    mock_run_command.return_value = (0, load_cmd_json_fixture)

    zpools = await list_pools(uid="1000")

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

    zpools = await get_pool_statuss(uid="1000")

    mock_data = json.loads(load_cmd_json_fixture)
    for pool in mock_data["pools"].values():
        assert _build_pool_state(pool) in zpools


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_get_importable_pools(mock_run_command, load_cmd_json_fixture):
    mock_run_command.return_value = (0, load_cmd_json_fixture)

    importable_pools = await get_importable_pools(1000)

    assert importable_pools == [
        ImportablePools(name="fish", id=1123, healthy=True),
        ImportablePools(name="tank", id=1234, healthy=False)
    ]


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_get_importable_pools_no_id(mock_run_command, load_cmd_json_fixture, caplog):
    mock_run_command.return_value = (0, load_cmd_json_fixture)

    with pytest.raises(AttributeError) as e:
        importable_pools = await get_importable_pools(1000)

    assert "No id field in zpool import" in str(e.value)
    assert "No id field in zpool import" in caplog.text


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_get_importable_pools_char_id(mock_run_command, load_cmd_json_fixture, caplog):
    mock_run_command.return_value = (0, load_cmd_json_fixture)

    with pytest.raises(ValueError) as e:
        importable_pools = await get_importable_pools(1000)

    assert "Found non-int characters in pool id field:" in str(e.value)
    assert "Found non-int characters in pool id field:" in caplog.text


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_import_pool(mock_run_command):
    pool_id = 4387097328
    mock_run_command.return_value = (0, "")

    await import_pool(1000, pool_id)


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_import_pool_custom_name(mock_run_command):
    pool_id = 4387097328
    mock_run_command.return_value = (0, "")

    await import_pool(1000, pool_id, "new_pool")


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_import_pool_no_pool(mock_run_command, caplog):
    pool_id = 4387097328
    mock_run_command.return_value = (1, f"cannot import '{pool_id}': no such pool available")

    with pytest.raises(FileNotFoundError) as e:
        await import_pool(1000, pool_id)

    assert f"cannot import '{pool_id}': no such pool available" in str(e.value)
    assert f"cannot import '{pool_id}': no such pool available" in caplog.text


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
@pytest.mark.parametrize(
    "func, mock_output",
    [
        (list_pools, ""),
        (get_pool_statuss, '{"output_version":{"command":"zpool status"},"pools":{}}'),
        (get_importable_pools, "no pools available to import")
    ]
)
async def test_empty_pool_collections(mock_run_command, func, mock_output):
    """Verifies that collection getters return empty lists on missing or blank data fields."""
    mock_run_command.return_value = (0, mock_output)
    
    result = await func(uid="1000")
    
    assert result == []
