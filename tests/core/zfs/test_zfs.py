import pytest
import json
from pathlib import Path
from unittest.mock import patch

from app.core.zfs.zfs import create_dataset, destroy_dataset, get_dataset, rename_dataset, create_snapshot, restore_snapshot, mount_dataset, unmount_dataset, load_key, unload_key, replicate_snapshot, _build_dataset_state
from app.core.zfs.models import PoolState, DatasetState
from app.core.errors import ZFSCommandFailedError
from app.core.config import settings


@pytest.mark.asyncio
@patch("app.core.zfs.zfs.execute_zfs_command")
@pytest.mark.parametrize(
    "create_parents, encryption_key",
    [
        (False, None),
        (True, None),
        (False, "encryption_key")
    ]
)
async def test_create_dataset(mock_execute, create_parents, encryption_key):
    parent_name = "tank"
    dataset_name = "turret"
    full_dataset_name = parent_name + "/" + dataset_name

    assert await create_dataset(1000, parent_name, dataset_name, create_parents=create_parents, encryption_key=encryption_key) is None
    
    mock_execute.assert_called_once()
    actual_uid, actual_command, actual_dataset = mock_execute.call_args[0]
    
    assert actual_uid == 1000
    assert actual_dataset == full_dataset_name
    
    assert actual_command[0] == settings.ZFS_BINARY
    assert "create" in actual_command
    
    if create_parents:
        assert "-p" in actual_command
        
    if encryption_key:
        assert "-o" in actual_command
        assert "encryption=on" in actual_command
        keylocation_arg = actual_command[-1] 
        assert keylocation_arg.startswith("keylocation=file:///")


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_create_dataset_no_parent(mock_run_command):
    parent_name = "tank"
    dataset_name = "turret"
    full_name = parent_name + "/" + dataset_name
    mock_run_command.return_value = (1, f"cannot create '{full_name}': no such pool 'tank'")

    with pytest.raises(FileNotFoundError):
        await create_dataset(1000, parent_name, dataset_name)


@pytest.mark.asyncio
@patch("app.core.zfs.zfs.execute_zfs_command")
@pytest.mark.parametrize(
    "recursive",
    [False, True]
)
async def test_destroy_dataset(mock_execute, recursive):
    dataset_name = "tank/turret"

    assert await destroy_dataset(1000, dataset_name, recursive=recursive) is None
    
    mock_execute.assert_called_once()
    if recursive:
        mock_execute.assert_called_with(1000, [settings.ZFS_BINARY, "destroy", dataset_name, "-r"], dataset_name)
    else:
        mock_execute.assert_called_with(1000, [settings.ZFS_BINARY, "destroy", dataset_name], dataset_name)


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_destroy_dataset_no_exist(mock_run_command):
    parent_name = "tank"
    dataset_name = "turret"
    full_name = parent_name + "/" + dataset_name
    mock_run_command.return_value = (1, f"cannot open '{full_name}': dataset does not exist")

    with pytest.raises(FileNotFoundError):
        await destroy_dataset(1000, full_name)


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
@pytest.mark.parametrize(
    "dataset, child_dataset, snapshot, detailed",
    [
        (None, False, False, False),
        ("tank/turret", True, False, False),
        (None, False, True, False),
        ("tank/turret", False, True, False),
        ("tank/turret", True, True, False),
        (None, False, False, True),
        ("tank/turret", False, True, True),
        ("tank/turret", True, True, True),
    ]
)
async def test_get_datasets(mock_run_command, dataset, child_dataset, snapshot, detailed, load_cmd_json_fixture):
    mock_run_command.return_value = (0, load_cmd_json_fixture)
    
    datasets = await get_dataset(1000, dataset, child_dataset, snapshot, detailed)

    mock_data = json.loads(load_cmd_json_fixture)

    assert len(datasets) == len(mock_data["datasets"])
    
    for mock_dataset in mock_data["datasets"].values():
        assert _build_dataset_state(mock_dataset, detailed=detailed) in datasets

    expected_command = [settings.ZFS_BINARY]
    if detailed:
        expected_command.extend(["get", "all"])
    else:
        expected_command.append("list")
    expected_command.append("-pj")
    if snapshot:
        expected_command.extend(["-t", "snapshot"])
    if child_dataset:
        expected_command.append("-r")
    if dataset:
        expected_command.append(dataset)
    
    mock_run_command.assert_called_with(1000, expected_command, 20)


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
@pytest.mark.parametrize(
    "dataset, detailed",
    [
        ("tank/gun", False),
        ("tank/turret", True),
    ]
)
async def test_get_dataset(mock_run_command, dataset, detailed, load_cmd_json_fixture):
    mock_run_command.return_value = (0, load_cmd_json_fixture)
    
    datasets = await get_dataset(1000, dataset, detailed=detailed)

    mock_data = json.loads(load_cmd_json_fixture)

    assert type(datasets) == DatasetState
    assert _build_dataset_state(next(iter(mock_data["datasets"].values())), detailed=detailed) == datasets

    expected_command = [settings.ZFS_BINARY]
    if detailed:
        expected_command.extend(["get", "all"])
    else:
        expected_command.append("list")
    expected_command.append("-pj")
    expected_command.append(dataset)
    
    mock_run_command.assert_called_with(1000, expected_command, 20)


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
@pytest.mark.parametrize(
    "snapshot",
    [False, True]
)
async def test_get_datasets_no_datasets(mock_run_command, snapshot, load_cmd_json_fixture):
    mock_run_command.return_value = (0, load_cmd_json_fixture)
    
    datasets = await get_dataset(1000, snapshot)

    assert datasets == []


@pytest.mark.asyncio
@patch("app.core.zfs.zfs.execute_zfs_command")
@pytest.mark.parametrize(
    "create_parents",
    [False, True]
)
async def test_rename_dataset(mock_execute, create_parents):
    old_dataset_name = "tank/storage/shell"
    new_dataset_name = "tank/turret/shell"

    assert await rename_dataset(1000, old_dataset_name, new_dataset_name, create_parents=create_parents) is None
    
    mock_execute.assert_called_once()
    if create_parents:
        mock_execute.assert_called_with(1000, [settings.ZFS_BINARY, "rename", old_dataset_name, new_dataset_name, "-p"], old_dataset_name, new_dataset_name)
    else:
        mock_execute.assert_called_with(1000, [settings.ZFS_BINARY, "rename", old_dataset_name, new_dataset_name], old_dataset_name, new_dataset_name)


@pytest.mark.asyncio
@patch("app.core.zfs.zfs.execute_zfs_command")
@pytest.mark.parametrize(
    "recursive",
    [False, True]
)
async def test_create_snapshot(mock_execute, recursive):
    uid = 1000
    dataset_name = "tank/turret"
    snapshot_name = "custom_snapshot"
    full_snapshot_name = dataset_name + "@" + snapshot_name

    assert await create_snapshot(uid, dataset_name, snapshot_name, recursive=recursive) is None
    
    mock_execute.assert_called_once()
    if recursive:
        mock_execute.assert_called_with(1000, [settings.ZFS_BINARY, "snapshot", full_snapshot_name, "-r"], dataset_name)
    else:
        mock_execute.assert_called_with(1000, [settings.ZFS_BINARY, "snapshot", full_snapshot_name], dataset_name)


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_create_snapshot_snapshot_exists(mock_run_command):
    mock_run_command.return_value = (1, "cannot create snapshot 'tank/turret@custom_snapshot': dataset already exists")

    uid = 1000
    dataset_name = "tank/turret"
    snapshot_name = "custom_snapshot"

    with pytest.raises(ZFSCommandFailedError):
        await create_snapshot(uid, dataset_name, snapshot_name)


@pytest.mark.asyncio
@patch("app.core.zfs.zfs.execute_zfs_command")
@pytest.mark.parametrize(
    "destructive",
    [False, True]
)
async def test_restore_snapshot(mock_execute, destructive):
    uid = 1000
    dataset_name = "tank/turret"
    snapshot_name = "custom_snapshot"
    full_snapshot_name = dataset_name + "@" + snapshot_name

    assert await restore_snapshot(uid, dataset_name, snapshot_name, destructive=destructive) is None
    
    mock_execute.assert_called_once()
    if destructive:
        mock_execute.assert_called_with(1000, [settings.ZFS_BINARY, "rollback", full_snapshot_name, "-r"], dataset_name)
    else:
        mock_execute.assert_called_with(1000, [settings.ZFS_BINARY, "rollback", full_snapshot_name], dataset_name)


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_restore_snapshot_destructive_required(mock_run_command, load_cmd_json_fixture):
    mock_run_command.return_value = (1,load_cmd_json_fixture)

    uid = 1000
    dataset_name = "tank/turret"
    snapshot_name = "second"

    with pytest.raises(ZFSCommandFailedError):
        await create_snapshot(uid, dataset_name, snapshot_name)


@pytest.mark.asyncio
@patch("app.core.zfs.zfs.load_key")
@patch("app.core.zfs.zfs.execute_zfs_command")
@pytest.mark.parametrize(
    "recursive, encryption_key",
    [(False, None), (True, None), (False, "encryption_key"), (True, "encryption_key")]
)
async def test_mount_dataset(mock_execute, mock_load_key, recursive, encryption_key):
    uid = 1000
    dataset_name = "tank/turret"

    assert await mount_dataset(1000, dataset_name, recursive=recursive, encryption_key=encryption_key) is None
    
    expected_command = [settings.ZFS_BINARY, "mount", dataset_name]

    if encryption_key:
        mock_load_key.assert_called_once()
        mock_load_key.assert_called_with(uid, dataset_name, encryption_key)

    if recursive:
        expected_command.append("-R")
    mock_execute.assert_called_once()
    mock_execute.assert_called_with(1000, expected_command, dataset_name)


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_mount_dataset_encrypted_incorrect_key(mock_run_command):
    mock_run_command.return_value = (1, "Key load error: Incorrect key provided for 'tank/turret/shell'")

    with pytest.raises(ZFSCommandFailedError):
        await mount_dataset(1000, "tank/turret", encryption_key="wrong_encryption_password")


@pytest.mark.asyncio
@patch("app.core.zfs.zfs.execute_zfs_command")
@pytest.mark.parametrize(
    "force, unload_key",
    [(False, False), (True, False), (False, True), (True, True)]
)
async def test_unmount_dataset(mock_execute, force, unload_key):
    uid = 1000
    dataset_name = "tank/turret"

    assert await unmount_dataset(1000, dataset_name, force=force, unload_key=unload_key) is None
    
    expected_command = [settings.ZFS_BINARY, "unmount", dataset_name]

    if force:
        expected_command.append("-f")
    if unload_key:
        expected_command.append("-u")
    mock_execute.assert_called_once()
    mock_execute.assert_called_with(1000, expected_command, dataset_name)


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_unmount_dataset_not_mounted(mock_run_command):
    mock_run_command.return_value = (1, "app.core.errors.ZFSCommandFailedError: cannot unmount 'tank/turret/shell': not currently mounted'")

    with pytest.raises(ZFSCommandFailedError):
        await unmount_dataset(1000, "tank/turret")

@pytest.mark.asyncio
@patch("app.core.zfs.zfs.execute_zfs_command")
async def test_load_key(mock_execute):
    dataset_name = "tank/turret"

    assert await load_key(1000, dataset_name, "encryption_password") == None

    mock_execute.assert_called_once()
    actual_uid, actual_command, actual_dataset = mock_execute.call_args[0]

    assert actual_uid == 1000
    assert actual_dataset == dataset_name

    expected_command = [settings.ZFS_BINARY, "load-key", dataset_name, "-L", "file://"]
    assert actual_command[:-1] == expected_command[:-1]

    assert actual_command[-1].startswith(expected_command[-1])


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_load_key_incorrect_key(mock_run_command):
    mock_run_command.return_value = (1, "Key load error: Incorrect key provided for 'tank/turret/shell'")

    with pytest.raises(ZFSCommandFailedError):
        await load_key(1000, "tank/turret", "wrong_encryption_password")


@pytest.mark.asyncio
@patch("app.core.zfs.zfs.execute_zfs_command")
@pytest.mark.parametrize(
    "recursive",
    [True, False]
)
async def test_unload_key(mock_execute, recursive):
    uid = 1000
    dataset_name = "tank/turret"

    assert await unload_key(1000, dataset_name, recursive=recursive) is None
    
    expected_command = [settings.ZFS_BINARY, "unload-key", dataset_name]

    if recursive:
        expected_command.append("-r")
    mock_execute.assert_called_once()
    mock_execute.assert_called_with(1000, expected_command, dataset_name)


@pytest.mark.asyncio
@patch("app.core.zfs.zfs.execute_zfs_replication")
@pytest.mark.parametrize(
    "incremental_from, recursive, remote_host, remote_sudo, encryption",
    [
        (None, False, False, False, False),
        ("tank/turret@yesterday", False, False, False, False),
        (None, True, False, False, False),
        (None, False, True, False, False),
        (None, False, True, True, False),
        (None, False, False, False, True),
        ("tank/turret@yesterday", True, False, False, False),
        ("tank/turret@yesterday", False, True, False, False),
        ("tank/turret@yesterday", False, True, False, True),
        ("tank/turret@yesterday", False, True, True, False),
        ("tank/turret@yesterday", True, True, True, False),
        ("tank/turret@yesterday", True, True, True, True),
    ]
)
async def test_replicate_snapshot(mock_execute, incremental_from, recursive, remote_host, remote_sudo, encryption):
    uid = 1000
    snapshot = "tank/turret@today"
    target = "tank/backup"

    assert await replicate_snapshot(1000, snapshot, target, incremental_from=incremental_from, recursive=recursive, remote_host=remote_host, remote_sudo=remote_sudo, encrypted=encryption) is None

    send_command = [settings.ZFS_BINARY, "send", "-R" if recursive else "-p"]
    if encryption:
        send_command.append("-w")
    if incremental_from:
        send_command.extend(["-i", incremental_from])
    send_command.append(snapshot)

    if remote_host:
        recv_command = ["ssh", remote_host]
        if remote_sudo:
            recv_command.append("sudo")
    else :
        recv_command = []
    recv_command.extend([settings.ZFS_BINARY, "receive", "-F", target])

    mock_execute.assert_called_once()
    mock_execute.assert_called_with(uid, send_command, recv_command, snapshot, target)