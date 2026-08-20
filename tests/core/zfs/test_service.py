import pytest
import json
from pathlib import Path
from unittest.mock import patch

from app.core.zfs.service import list_pools, _build_pool_state
from app.core.zfs.models import PoolState

def test_build_pool_state():
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
        size="10000",
        allocated="1000",
        free="9000"
    )

    return_pool = _build_pool_state(test_dict)

    assert type(return_pool) == PoolState

    assert return_pool == test_pool

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


