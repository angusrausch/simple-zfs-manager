import pytest
import json
from pathlib import Path
from unittest.mock import patch

from app.core.zfs.zfs import create_dataset, destroy_dataset, list_dataset, list_datasets, rename_dataset, create_snapshot, list_child_datasets, list_snapshots, restore_snapshot, mount_dataset, unmount_dataset, load_key, unload_key, get_datasets, get_dataset, _build_dataset_state
from app.core.zfs.models import PoolState
from app.core.errors import ZFSCommandFailedError


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_create_dataset(mock_run_command):
    parent_name = "tank"
    dataset_name = "turret"
    mock_run_command.return_value = (0, "")

    response = await create_dataset(1000, parent_name, dataset_name)
    assert response == None

@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_create_dataset_no_parent(mock_run_command, caplog):
    parent_name = "tank"
    dataset_name = "turret"
    full_name = parent_name + "/" + dataset_name
    mock_run_command.return_value = (1, f"cannot create '{full_name}': no such pool 'tank'")

    with pytest.raises(FileNotFoundError) as e:
        await create_dataset(1000, parent_name, dataset_name)

    assert f"cannot create '{full_name}': no such pool '{parent_name}'" in str(e.value)
    assert f"cannot create '{full_name}': no such pool '{parent_name}'" in caplog.text


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_create_dataset_create_parents(mock_run_command):
    parent_name = "tank/turret"
    dataset_name = "shell"
    mock_run_command.return_value = (0, "")

    response = await create_dataset(1000, parent_name, dataset_name, create_parents=True)
    assert response == None


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_create_dataset_encryption(mock_run_command):
    parent_name = "tank/turret"
    dataset_name = "shell"
    mock_run_command.return_value = (0, "")

    response = await create_dataset(1000, parent_name, dataset_name, encryption="encryption_password")
    assert response == None


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_destroy_dataset(mock_run_command):
    parent_name = "tank"
    dataset_name = "turret"
    full_name = parent_name + "/" + dataset_name
    mock_run_command.return_value = (0, "")

    response = await destroy_dataset(1000, full_name)
    assert response == None


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_destroy_dataset_recursive(mock_run_command):
    parent_name = "tank"
    dataset_name = "turret"
    full_name = parent_name + "/" + dataset_name
    mock_run_command.return_value = (0, "")

    response = await destroy_dataset(1000, full_name, recursive=True)
    assert response == None


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_destroy_dataset_no_exist(mock_run_command, caplog):
    parent_name = "tank"
    dataset_name = "turret"
    full_name = parent_name + "/" + dataset_name
    mock_run_command.return_value = (1, f"cannot open '{full_name}': dataset does not exist")

    with pytest.raises(FileNotFoundError) as e:
        await destroy_dataset(1000, full_name)

    assert f"cannot open '{full_name}': dataset does not exist" in str(e.value)
    assert f"cannot open '{full_name}': dataset does not exist" in caplog.text


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_list_datasets(mock_run_command, load_cmd_json_fixture):
    mock_run_command.return_value = (0, load_cmd_json_fixture)
    
    datasets = await list_datasets(1000)

    mock_data = json.loads(load_cmd_json_fixture)
    assert len(datasets) == len(mock_data["datasets"])
    
    for mock_dataset in mock_data["datasets"].values():
        assert _build_dataset_state(mock_dataset) in datasets


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_list_child_datasets(mock_run_command, load_cmd_json_fixture):
    mock_run_command.return_value = (0, load_cmd_json_fixture)

    datasets = await list_child_datasets(1000, "tank/turret")

    mock_data = json.loads(load_cmd_json_fixture)
    assert len(datasets) == len(mock_data["datasets"])
    
    for mock_dataset in mock_data["datasets"].values():
        assert _build_dataset_state(mock_dataset) in datasets


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_list_datasets_no_datasets(mock_run_command, load_cmd_json_fixture):
    mock_run_command.return_value = (0, load_cmd_json_fixture)
    
    datasets = await list_datasets(1000)

    assert datasets == []


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_list_dataset(mock_run_command, load_cmd_json_fixture):
    mock_run_command.return_value = (0, load_cmd_json_fixture)
    dataset_name = "tank/gun"

    dataset = await list_dataset(1000, dataset_name)

    mock_data = json.loads(load_cmd_json_fixture)
    assert _build_dataset_state(mock_data["datasets"][dataset_name]) == dataset


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_rename_dataset(mock_run_command):
    mock_run_command.return_value = (0, "")

    old_dataset_name = "tank/storage/shell"
    new_dataset_name = "tank/shell"

    response = await rename_dataset(1000, old_dataset_name, new_dataset_name)
    assert response == None


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_rename_dataset_create_parent(mock_run_command):
    mock_run_command.return_value = (0, "")

    old_dataset_name = "tank/storage/shell"
    new_dataset_name = "tank/turret/shell"

    response = await rename_dataset(1000, old_dataset_name, new_dataset_name, create_parents=True)
    assert response == None


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_create_snapshot(mock_run_command):
    mock_run_command.return_value = (0, "")

    uid = 1000
    dataset_name = "tank/turret"
    snapshot_name = "custom_snapshot"

    response = await create_snapshot(uid, dataset_name, snapshot_name)

    assert response == None


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_create_snapshot_recursive(mock_run_command):
    mock_run_command.return_value = (0, "")

    uid = 1000
    dataset_name = "tank/turret"
    snapshot_name = "custom_snapshot"

    response = await create_snapshot(uid, dataset_name, snapshot_name, recursive=True)

    assert response == None


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_create_snapshot_snapshot_exists(mock_run_command, caplog):
    mock_run_command.return_value = (1, "cannot create snapshot 'tank/turret@custom_snapshot': dataset already exists")

    uid = 1000
    dataset_name = "tank/turret"
    snapshot_name = "custom_snapshot"

    with pytest.raises(ZFSCommandFailedError) as e:
        await create_snapshot(uid, dataset_name, snapshot_name)

    assert "cannot create snapshot 'tank/turret@custom_snapshot': dataset already exists" in str(e.value)
    assert "[CMD] cannot create snapshot 'tank/turret@custom_snapshot': dataset already exists" in caplog.text


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_restore_snapshot(mock_run_command):
    mock_run_command.return_value = (0, "")

    uid = 1000
    dataset_name = "tank/turret"
    snapshot_name = "custom_snapshot"

    response = await restore_snapshot(uid, dataset_name, snapshot_name)

    assert response == None


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_restore_snapshot_destructive(mock_run_command):
    mock_run_command.return_value = (0, "")

    uid = 1000
    dataset_name = "tank/turret"
    snapshot_name = "custom_snapshot"

    response = await restore_snapshot(uid, dataset_name, snapshot_name, destructive=True)

    assert response == None


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_restore_snapshot_destructive_required(mock_run_command, load_cmd_json_fixture, caplog):
    mock_run_command.return_value = (1,load_cmd_json_fixture)

    uid = 1000
    dataset_name = "tank/turret"
    snapshot_name = "second"

    with pytest.raises(ZFSCommandFailedError) as e:
        await create_snapshot(uid, dataset_name, snapshot_name)

    assert "Cannot restore to snapshot where snapshots exist between target and current, use the destructive option to delete these snapshots." in str(e.value)


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_list_snapshots(mock_run_command, load_cmd_json_fixture):
    mock_run_command.return_value = (0, load_cmd_json_fixture)

    datasets = await list_snapshots(1000)

    mock_data = json.loads(load_cmd_json_fixture)
    assert len(datasets) == len(mock_data["datasets"])
    
    for mock_dataset in mock_data["datasets"].values():
        assert _build_dataset_state(mock_dataset) in datasets


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_list_snapshots_no_snapshots(mock_run_command, load_cmd_json_fixture):
    mock_run_command.return_value = (0, load_cmd_json_fixture)

    datasets = await list_snapshots(1000)

    assert datasets == []


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_list_snapshots_name(mock_run_command, load_cmd_json_fixture):
    mock_run_command.return_value = (0, load_cmd_json_fixture)

    datasets = await list_snapshots(1000, "tank/turret")

    mock_data = json.loads(load_cmd_json_fixture)
    assert len(datasets) == len(mock_data["datasets"])
    
    for mock_dataset in mock_data["datasets"].values():
        assert _build_dataset_state(mock_dataset) in datasets


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_mount_dataset(mock_run_command):
    mock_run_command.return_value = (0, "")

    response = await mount_dataset(1000, "tank/turret")

    assert response == None


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_mount_dataset_recursive(mock_run_command):
    mock_run_command.return_value = (0, "")

    response = await mount_dataset(1000, "tank/turret", recursive=True)

    assert response == None


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_mount_dataset_encrypted(mock_run_command):
    mock_run_command.return_value = (0, "")

    response = await mount_dataset(1000, "tank/turret", encryption="encryption_password")

    assert response == None


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_mount_dataset_encrypted_incorrect_key(mock_run_command, caplog):
    mock_run_command.return_value = (1, "Key load error: Incorrect key provided for 'tank/turret/shell'")

    with pytest.raises(ZFSCommandFailedError) as e:
        await mount_dataset(1000, "tank/turret", encryption="wrong_encryption_password")

    assert "Key load error: Incorrect key provided for 'tank/turret/shell'" in str(e.value)
    assert "[CMD] Key load error: Incorrect key provided for 'tank/turret/shell'" in caplog.text


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_unmount_dataset(mock_run_command):
    mock_run_command.return_value = (0, "")

    response = await unmount_dataset(1000, "tank/turret")

    assert response == None


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_mount_dataset_force(mock_run_command):
    mock_run_command.return_value = (0, "")

    response = await unmount_dataset(1000, "tank/turret", force=True)

    assert response == None


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_unmount_dataset_encrypted(mock_run_command):
    mock_run_command.return_value = (0, "")

    response = await unmount_dataset(1000, "tank/turret", unload_key=True)

    assert response == None


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_unmount_dataset_not_mounted(mock_run_command, caplog):
    mock_run_command.return_value = (1, "app.core.errors.ZFSCommandFailedError: cannot unmount 'tank/turret/shell': not currently mounted'")

    with pytest.raises(ZFSCommandFailedError) as e:
        await unmount_dataset(1000, "tank/turret")

    assert "cannot unmount 'tank/turret/shell': not currently mounted'" in str(e.value)
    assert "cannot unmount 'tank/turret/shell': not currently mounted'" in caplog.text


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_load_key(mock_run_command):
    mock_run_command.return_value = (0, "")

    response = await load_key(1000, "tank/turret", "encryption_password")

    assert response == None


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_load_key_incorrect_key(mock_run_command, caplog):
    mock_run_command.return_value = (1, "Key load error: Incorrect key provided for 'tank/turret/shell'")

    with pytest.raises(ZFSCommandFailedError) as e:
        await load_key(1000, "tank/turret", "wrong_encryption_password")

    assert "Key load error: Incorrect key provided for 'tank/turret/shell'" in str(e.value)
    assert "[CMD] Key load error: Incorrect key provided for 'tank/turret/shell'" in caplog.text


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_unload_key(mock_run_command):
    mock_run_command.return_value = (0, "")

    response = await unload_key(1000, "tank/turret")

    assert response == None


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_unload_key_recursive(mock_run_command):
    mock_run_command.return_value = (0, "")

    response = await unload_key(1000, "tank/turret", recursive=True)

    assert response == None


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_get_datasets(mock_run_command, load_cmd_json_fixture):
    mock_run_command.return_value = (0, load_cmd_json_fixture)
    
    datasets = await get_datasets(1000)

    mock_data = json.loads(load_cmd_json_fixture)
    assert len(datasets) == len(mock_data["datasets"])
    
    for mock_dataset in mock_data["datasets"].values():
        assert _build_dataset_state(mock_dataset, detailed=True) in datasets


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_get_dataset(mock_run_command, load_cmd_json_fixture):
    mock_run_command.return_value = (0, load_cmd_json_fixture)
    dataset_name = "tank"

    dataset = await get_dataset(1000, dataset_name)

    mock_data = json.loads(load_cmd_json_fixture)
    assert _build_dataset_state(mock_data["datasets"][dataset_name], detailed=True) == dataset