import pytest
from unittest.mock import patch, AsyncMock

from app.core.zfs.utils import execute_zfs_command, execute_zfs_command_json, execute_zfs_replication
from app.core.errors import ZFSCommandFailedError


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_execute_zfs_command(mock_run, caplog):
    mock_run.return_value = (0, "this should be in the return")
    
    response = await execute_zfs_command(uid="1000", command=["dummy", "command"])
    
    assert response == "this should be in the return"


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
@pytest.mark.parametrize(
    "output, error_msg",
    [
        ("mirror requires at least 2 devices", "Not enough disks selected for Mirror, must use at least 2 disks"),
        ("raidz1 requires at least 2 devices", "Not enough disks selected for RAIDZ1, must use at least 2 disks"),
        ("raidz2 requires at least 3 devices", "Not enough disks selected for RAIDZ2, must use at least 3 disks"),
        ("raidz3 requires at least 4 devices", "Not enough disks selected for RAIDZ3, must use at least 4 disks"),
        ("use '-f' to override the following errors:\nraidz contains devices of different sizes",
                "The following Error occured, Use force option to override:\n'raidz contains devices of different sizes")
    ]
)
async def test_execute_zfs_command_invalid_vdev(mock_run, output, error_msg, caplog):
    mock_run.return_value = (1, "invalid vdev specification: " + output)
    
    with pytest.raises(ZFSCommandFailedError) as e:
        await execute_zfs_command(uid="1000", command=["zpool", "list"])
        
    assert error_msg in caplog.text
    assert error_msg in str(e.value)


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
@pytest.mark.parametrize(
    "output, command, pool, error_msg",
    [
        ("cannot open 'tank': no such pool", ["zpool", "list", "tank"], "tank",
                "cannot open 'tank': no such pool"),
        ("cannot open 'tank/turret': dataset does not exist", ["zfs", "list", "tank"], "tank/turret",
                "cannot open 'tank/turret': dataset does not exist"),
    ]
)
async def test_execute_zfs_command_missing_dataset(mock_run, output, command, pool, error_msg, caplog):
    mock_run.return_value = (1, output)
    
    with pytest.raises(FileNotFoundError) as e:
        await execute_zfs_command(uid="1000", command=command, pool_name=pool)
        
    assert f"[CMD] {error_msg}" in caplog.text
    assert error_msg in str(e.value)


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_execute_zfs_command_missing_parents(mock_run, caplog):
    mock_run.return_value = (1, "cannot create 'tank/turret/shell': parent does not exist")
    
    with pytest.raises(FileNotFoundError) as e:
        await execute_zfs_command(uid="1000", command=["zfs", "create", "tank/turret/shell"], pool_name="tank/turret/shell")
        
    assert "[CMD] The following Error occured, Use create parents option to override:\n'cannot create 'tank/turret/shell': parent does not exist'" in caplog.text
    assert "The following Error occured, Use create parents option to override:\n'cannot create 'tank/turret/shell': parent does not exist'" in str(e.value)



@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_execute_zfs_command_missing_dataset(mock_run, caplog):
    mock_run.return_value = (1, "cannot rollback to 'tank/turret@now': more recent snapshots or bookmarks exist\nuse '-r' to force deletion of the following snapshots and bookmarks:\ntank/turret@future")
    
    with pytest.raises(ZFSCommandFailedError) as e:
        await execute_zfs_command(uid="1000", command=["zfs", "rollback", "tank/turret@now"], pool_name="tank/turret")
        
    assert f"[CMD] Cannot restore to snapshot where snapshots exist between target and current, use the destructive option to delete these snapshots.\nThe following snapshots are required to be removed:\ntank/turret@future" in caplog.text
    assert "Cannot restore to snapshot where snapshots exist between target and current, use the destructive option to delete these snapshots.\nThe following snapshots are required to be removed:\ntank/turret@future" in str(e.value)

@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_execute_zfs_command_json(mock_run, caplog):
    mock_run.return_value = (0, "{\"value\":\"valid\"}")
    
    response = await execute_zfs_command_json(uid="1000", command=["dummy", "command"])
    
    assert type(response) == dict
    assert response["value"] == "valid"


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_execute_zfs_command_json_empty(mock_run, caplog):
    for mock_values in ["", "no datasets available"]:
        mock_run.return_value = (0, mock_values)

        response = await execute_zfs_command_json(uid="1000", command=["dummy", "command"])
        
        assert type(response) == dict
        assert response == {}


@pytest.mark.asyncio
@patch("app.core.zfs.utils.asyncio.create_subprocess_exec")
async def test_execute_zfs_replication(mock_create_exec):
    mock_send_proc = AsyncMock()
    mock_send_proc.returncode = 0
    mock_send_proc.communicate = AsyncMock(return_value=(b"", b""))

    mock_recv_proc = AsyncMock()
    mock_recv_proc.returncode = 0
    mock_recv_proc.communicate = AsyncMock(return_value=(b"", b""))

    mock_create_exec.side_effect = [mock_send_proc, mock_recv_proc]

    with patch("app.core.zfs.utils.os.pipe", return_value=(0, 0)), \
         patch("app.core.zfs.utils.os.close"):

        response =await execute_zfs_replication(
            uid=1000,
            send_command=["zfs", "send", "tank/turret@now"],
            recv_command=["zfs", "recv", "tank/backup"],
            snapshot="tank/turret@now",
            target="tank/backup"
        )

        assert response == None

@pytest.mark.asyncio
@patch("app.core.zfs.utils.asyncio.create_subprocess_exec")
async def test_execute_zfs_replication_already_exists(mock_create_exec):
    mock_send_proc = AsyncMock()
    mock_send_proc.returncode = -13
    mock_send_proc.communicate = AsyncMock(return_value=(b"", b""))

    mock_recv_proc = AsyncMock()
    mock_recv_proc.returncode = 1
    mock_recv_proc.communicate = AsyncMock(return_value=(
        b"", 
        b"cannot receive incremental stream: destination library/dataset already exists"
    ))

    mock_create_exec.side_effect = [mock_send_proc, mock_recv_proc]

    with patch("app.core.zfs.utils.os.pipe", return_value=(3, 4)), \
         patch("app.core.zfs.utils.os.close"):

        with pytest.raises(ZFSCommandFailedError) as exc_info:
            await execute_zfs_replication(
                uid=1000,
                send_command=["zfs", "send", "tank/turret@now"],
                recv_command=["zfs", "recv", "tank/backup"],
                snapshot="tank/turret@now",
                target="tank/backup"
            )

        assert mock_create_exec.call_count == 2
        
        assert "cannot receive incremental stream: destination library/dataset already exists" in str(exc_info.value)


@pytest.mark.asyncio
@patch("app.core.zfs.utils.asyncio.create_subprocess_exec")
async def test_execute_zfs_replication_source_does_not_exist(mock_create_exec):
    mock_send_proc = AsyncMock()
    mock_send_proc.returncode = 1
    mock_send_proc.communicate = AsyncMock(return_value=(
        b"", 
        b"'tank/turret@now': dataset does not exist"
    ))

    mock_recv_proc = AsyncMock()
    mock_recv_proc.returncode = -13
    mock_recv_proc.communicate = AsyncMock(return_value=(b"", b""))

    mock_create_exec.side_effect = [mock_send_proc, mock_recv_proc]

    with patch("app.core.zfs.utils.os.pipe", return_value=(3, 4)), \
         patch("app.core.zfs.utils.os.close"):

        with pytest.raises(FileNotFoundError) as exc_info:
            await execute_zfs_replication(
                uid=1000,
                send_command=["zfs", "send", "tank/turret@now"],
                recv_command=["zfs", "recv", "tank/backup"],
                snapshot="tank/turret@now",
                target="tank/backup"
            )

        assert mock_create_exec.call_count == 2
        assert "dataset does not exist" in str(exc_info.value)
