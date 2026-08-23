import pytest
from unittest.mock import patch

from app.core.zfs.utils import execute_zfs_command
from app.core.errors import ZFSCommandFailedError


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
@pytest.mark.parametrize(
    "exit_status, output, expected_exception, error_msg",
    [
        (127, "Error...", FileNotFoundError, "Command zpool not found, ensure `zfs` is installed"),
        (2, "Error...", AssertionError, "Zpool appears to be different version. Arguments not parsing"),
        (1, "Generic Error", ZFSCommandFailedError, "Generic Error"),
    ]
)
async def test_execute_zfs_command_errors(mock_run, exit_status, output, expected_exception, error_msg, caplog):
    mock_run.return_value = (exit_status, output)
    
    with pytest.raises(expected_exception) as e:
        await execute_zfs_command(uid="1000", command=["zpool", "list"])
        
    assert error_msg in caplog.text
    assert error_msg in str(e.value)


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_execute_zfs_command_missing_pool(mock_run, caplog):
    mock_run.return_value = (1, "cannot open 'tank': no such pool")
    
    with pytest.raises(FileNotFoundError) as e:
        await execute_zfs_command(uid="1000", command=["zpool", "list", "tank"], pool_name="tank")
        
    assert "[CMD] cannot open 'tank': no such pool" in caplog.text
    assert "cannot open 'tank': no such pool" in str(e.value)


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_execute_zfs_command_missing_dataset(mock_run, caplog):
    mock_run.return_value = (1, "cannot open 'tank/turret': dataset does not exist")
    
    with pytest.raises(FileNotFoundError) as e:
        await execute_zfs_command(uid="1000", command=["zpool", "list", "tank"], pool_name="tank/turret")
        
    assert "[CMD] cannot open 'tank/turret': dataset does not exist" in caplog.text
    assert "cannot open 'tank/turret': dataset does not exist" in str(e.value)
