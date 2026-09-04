import pytest
from unittest.mock import patch
from pathlib import Path

from app.core.smb.smb import list_shares, get_share, create_share, _get_param, _set_param, add_share_user, del_share_user, _execute_smb_command, set_share_browseable, get_share_browseable, set_share_guest_ok, get_share_guest_ok, set_share_read_only, get_share_read_only
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
@patch("app.core.smb.smb._execute_smb_command")
async def test_get_share(mock_run_command, load_cmd_json_fixture):
    mock_run_command.return_value = load_cmd_json_fixture
    
    share = await get_share(1000, "test")

    expected_share = SmbShare(name='test', path=Path('/fast/test'), browsable=False, read_only=True, 
            public=False, users=['angus', 'test_samaba_user'], force_user=None, create_mask=0o500, dir_mask=0o500)

    assert share == expected_share


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_execute_smb_command(mock_run):
    mock_run.return_value = (0, "success")
    
    assert await _execute_smb_command("1000", ["list"]) == "success"


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
@pytest.mark.parametrize(
    "return_code, return_message, error_type, error_message, share_name",
    [
        (127, "/usr/bin/net: command not found", FileNotFoundError, "Command `/usr/bin/net` not found, ensure it is installed", None),
        (126, "Failed to initialize the registry: WERR_ACCESS_DENIED", PermissionError, "Invalid Permissions: Failed to initialize the registry: WERR_ACCESS_DENIED", None),
        (255, "Failed to initialize the registry: WERR_ACCESS_DENIED", PermissionError, "Invalid Permissions: Failed to initialize the registry: WERR_ACCESS_DENIED", None),
        (1, "Generic Error", Exception, "An error occured: Generic Error", None),
        (1, "error getting share parameters: SBC_ERR_NO_SUCH_SERVICE", KeyError, "Share does not exist: 'test'", "test"),
    ]
)
async def test_execute_smb_command_error(mock_run, return_code, return_message, error_type, error_message, share_name, caplog):
    mock_run.return_value = (return_code, return_message)

    with pytest.raises(error_type) as e:
        await _execute_smb_command("1000", ["list"], share_name=share_name)

    assert f"[CMD] {error_message}" in caplog.text
    assert error_message in str(e.value)


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
@pytest.mark.parametrize(
    "return_code, return_message, custom_return",
    [
        (255, "Error: given parameter 'browseable' is not set.", None),
    ]
)
async def test_execute_smb_command_custom_return(mock_run, return_code, return_message, custom_return):
    mock_run.return_value = (return_code, return_message)

    assert await _execute_smb_command("1000", ["list"], share_name="test_share") == custom_return


@pytest.mark.asyncio
@patch("app.core.smb.smb._execute_smb_command")
@pytest.mark.parametrize(
    "share_name, share_path, writable, guest_ok",
    [
        ("test", "/test/path", False, False),
        ("test_two", "/test/path/two", False, False),
        ("test", "/test/path", True, False),
        ("test", "/test/path", False, True),
        ("test", "/test/path", True, True),
    ]
)
async def test_create_share(mock_run, share_name, share_path, writable, guest_ok):
    assert await create_share(1000, share_name, share_path, writable, guest_ok) == None
    
    if writable:
        writeable_param = "writeable=y"
    else:
        writeable_param = "writeable=n"

    if guest_ok:
        guest_ok_param = "guest_ok=y"
    else:
        guest_ok_param = "guest_ok=n"

    mock_run.assert_called_once()
    mock_run.assert_called_with(1000, ["addshare", share_name, share_path, writeable_param, guest_ok_param], share_name)


@pytest.mark.asyncio
@patch("app.core.smb.smb.async_run_command")
async def test_execute_smb_command_builds_command(mock_execute):
    mock_execute.return_value = (0, "success")

    await _execute_smb_command(1000, ["list", "more_list"])
    
    mock_execute.assert_called_once()
    mock_execute.assert_called_with(1000, ["/usr/bin/net", "conf", "list", "more_list"])


@pytest.mark.asyncio
@patch("app.core.smb.smb._execute_smb_command")
async def test_get_parm(mock_execute):
    mock_return = "angus, jeff"
    mock_execute.return_value = mock_return

    assert await _get_param(1000, "test_share", "valid users") == mock_return
    
    mock_execute.assert_called_once()
    mock_execute.assert_called_with(1000, ["getparm", "test_share", "valid users"], "test_share")


@pytest.mark.asyncio
@patch("app.core.smb.smb._execute_smb_command")
async def test_set_parm(mock_execute):
    assert await _set_param(1000, "test_share", "public_ok", "y") is None
    
    mock_execute.assert_called_once()
    mock_execute.assert_called_with(1000, ["setparm", "test_share", "public_ok", "y"], "test_share")


@pytest.mark.asyncio
@patch("app.core.smb.smb._set_param")
@patch("app.core.smb.smb._get_param")
@pytest.mark.parametrize(
    "user, expected_arg",
    [
        ("peter", "angus, jeff, peter"), (["peter", "greg"], "angus, jeff, peter, greg")
    ]
)
async def test_add_share_user(mock_get, mock_set, user, expected_arg):
    mock_get.return_value = "angus, jeff"

    assert await add_share_user(1000, "test_share", user) is None

    mock_get.assert_called_once()
    mock_get.assert_called_with(1000, "test_share", "valid users")

    mock_set.assert_called_once()
    mock_set.assert_called_with(1000, "test_share", "valid users", expected_arg)


@pytest.mark.asyncio
@patch("app.core.smb.smb._set_param")
@patch("app.core.smb.smb._get_param")
@pytest.mark.parametrize(
    "user, expected_arg",
    [
        ("peter", "angus, jeff, greg"), (["peter", "greg"], "angus, jeff")
    ]
)
async def test_del_share_user(mock_get, mock_set, user, expected_arg):
    mock_get.return_value = "angus, jeff, peter, greg"

    assert await del_share_user(1000, "test_share", user) is None

    mock_get.assert_called_once()
    mock_get.assert_called_with(1000, "test_share", "valid users")

    mock_set.assert_called_once()
    mock_set.assert_called_with(1000, "test_share", "valid users", expected_arg)


@pytest.mark.asyncio
@patch("app.core.smb.smb._get_param")
@pytest.mark.parametrize(
    "method, user, return_value",
    [
        (add_share_user, "peter", "angus, jeff, greg, peter"),
        (del_share_user, "peter", "angus, jeff, greg"),
        (add_share_user, ["tony", "peter"], "angus, jeff, greg, peter"),
        (del_share_user, ["greg", "peter"], "angus, jeff, greg"),
        (del_share_user, ["peter", "greg"], "angus, jeff, greg"),
    ]
)
async def test_add_del_share_user_no_user(mock_get, method, user, return_value):
    mock_get.return_value = return_value

    with pytest.raises(ValueError):
        await method(1000, "test_share", user)


@pytest.mark.asyncio
@patch("app.core.smb.smb._set_param")
@pytest.mark.parametrize(
    "method, param",
    [
        (set_share_browseable, "browseable"),
        (set_share_guest_ok, "guest ok"),
        (set_share_read_only, "read only")
    ]
)
async def test_set_share_boolean(mock_execute, method, param):
    assert await method(1000, "test_share", True) is None

    mock_execute.assert_called_once()
    mock_execute.assert_called_with(1000, "test_share", param, "yes")

    mock_execute.reset_mock()

    assert await method(1000, "test_share", False) is None

    mock_execute.assert_called_once()
    mock_execute.assert_called_with(1000, "test_share", param, "no")


@pytest.mark.asyncio
@patch("app.core.smb.smb._get_param")
@pytest.mark.parametrize(
    "method, param, default",
    [
        (get_share_browseable, "browseable", True),
        (get_share_guest_ok, "guest ok", False),
        (get_share_read_only, "read only", True)
    ]
)
async def test_get_share_boolean(mock_execute, method, param, default):
    mock_execute.return_value = "yes"
    assert await method(1000, "test_share") is True

    mock_execute.assert_called_once()
    mock_execute.assert_called_with(1000, "test_share", param)

    mock_execute.return_value = "no"
    assert await method(1000, "test_share") is False

    mock_execute.return_value = f"Error: given parameter '{param}' is not set."
    assert await method(1000, "test_share") is default