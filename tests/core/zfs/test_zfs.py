import pytest
import json
from pathlib import Path
from unittest.mock import patch

from app.core.zfs.zfs import create_dataset, destroy_dataset
from app.core.errors import ZFSCommandFailedError


@pytest.mark.asyncio
@patch("app.core.system.runner.run_command")
async def test_create_dataset(mock_run_command):
    parent_name = "tank"
    dataset_name = "turret"
    mock_run_command.return_value = (0, "")

    await create_dataset(1000, parent_name, dataset_name)


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
async def test_destroy_dataset(mock_run_command):
    parent_name = "tank"
    dataset_name = "turret"
    full_name = parent_name + "/" + dataset_name
    mock_run_command.return_value = (0, "")

    await destroy_dataset(1000, full_name)


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