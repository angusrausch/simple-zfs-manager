import pytest
from unittest.mock import patch
from pathlib import Path

from app.core.smb.smb import list_shares, _execute_smb_command
from app.core.smb.models import SmbShare

@pytest.mark.asyncio
@patch("app.core.smb.smb._execute_smb_command")
async def test_list_smb_shares(mock_run_command, load_cmd_json_fixture):
    mock_run_command.return_value = load_cmd_json_fixture
    
    shares = await list_shares(1000)

    expected_shares = [
        SmbShare(name='angus', path=Path('/fast/angus'), browsable=True, read_only=False, 
            public=False, users=['angus'], force_user=None, create_mask=432, dir_mask=432), 
        SmbShare(name='test', path=Path('/fast/test'), browsable=False, read_only=True, 
            public=False, users=['angus', 'test_samaba_user'], force_user=None, create_mask=0o500, dir_mask=0o500),
        SmbShare(name='test2', path=Path('/fast/test2'), browsable=False, read_only=True, 
            public=False, users=[], force_user=None, create_mask=0o500, dir_mask=0o500),
    ]

    for expected_share in expected_shares:
        assert expected_share in shares

    assert len(shares) == len(expected_shares)


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_execute_smb_command(mock_run):
    mock_run.return_value = (0, "success")
    
    assert await _execute_smb_command(uid="1000", command=["net", "conf", "list"]) == "success"


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
@pytest.mark.parametrize(
    "return_code, return_message, error_type, error_message",
    [
        (127, "net: command not found", FileNotFoundError, "Command `net` not found, ensure it is installed"),
        (126, "Failed to initialize the registry: WERR_ACCESS_DENIED", PermissionError, "Invalid Permissions: Failed to initialize the registry: WERR_ACCESS_DENIED"),
        (255, "Failed to initialize the registry: WERR_ACCESS_DENIED", PermissionError, "Invalid Permissions: Failed to initialize the registry: WERR_ACCESS_DENIED"),
        (1, "Generic Error", Exception, "An error occured: Generic Error"),
    ]
)
async def test_execute_smb_command_error(mock_run, return_code, return_message, error_type, error_message, caplog):
    mock_run.return_value = (return_code, return_message)

    with pytest.raises(error_type) as e:
        await _execute_smb_command(uid="1000", command=["net", "conf", "list"])

    assert f"[CMD] {error_message}" in caplog.text
    assert error_message in str(e.value)
