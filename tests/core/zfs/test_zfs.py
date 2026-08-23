import pytest
import json
from pathlib import Path
from unittest.mock import patch

from app.core.zfs.zfs import create_dataset, destroy_dataset, list_dataset, list_datasets, rename_dataset, _build_dataset_state
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
async def test_destroy_dataset(mock_run_command):
    parent_name = "tank"
    dataset_name = "turret"
    full_name = parent_name + "/" + dataset_name
    mock_run_command.return_value = (0, "")

    response = await destroy_dataset(1000, full_name)
    assert response == None


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_destroy_dataset_no_parent(mock_run_command, caplog):
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