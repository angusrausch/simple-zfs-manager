import pytest
from unittest.mock import patch

from app.core.disk_management import list_disks, list_unused_disks, _get_disk_json


@patch("app.core.disk_management._get_disk_json")
def test_list_disks(mock_run_command, load_cmd_json_fixture):
    mock_run_command.return_value = (load_cmd_json_fixture)

    disks = list_disks(1000)

    expected_disks = [
            {'name': 'sda', 'size': 240057409536, 'mounted': False}, 
            {'name': 'sdb', 'size': 240057409536, 'mounted': False}, 
            {'name': 'sdc', 'size': 250059350016, 'mounted': False}, 
            {'name': 'sdd', 'size': 250059350016, 'mounted': False}, 
            {'name': 'mmcblk0', 'size': 127865454592, 'mounted': True}
        ]
    assert disks == expected_disks


@patch("app.core.disk_management.run_command")
def test_get_disk_json(mock_run_command, load_cmd_json_fixture):
    mock_run_command.return_value = (0, load_cmd_json_fixture)

    disks = _get_disk_json(1000)

    expected_return = [ 
        {'name': 'sdd', 'size': 250059350016, 'mountpoint': None, 'children': 
            [
                {'name': 'sdd1', 'size': 250049724416, 'mountpoint': None}, 
                {'name': 'sdd9', 'size': 8388608, 'mountpoint': None}
            ]
        }, 
        {'name': 'mmcblk0', 'size': 127865454592, 'mountpoint': None, 'children': 
            [
                {'name': 'mmcblk0p1', 'size': 536870912, 'mountpoint': '/boot/firmware'}, 
                {'name': 'mmcblk0p2', 'size': 63319310336, 'mountpoint': '/'}
            ]
        }
    ]
    assert disks == expected_return


@pytest.mark.asyncio
@patch("app.core.disk_management.list_disks")
@patch("app.core.disk_management.get_used_disks")
async def test_list_unused_disks(mock_get_used_disks, mock_list_disks, load_cmd_json_fixture):
    mock_list_disks.return_value = load_cmd_json_fixture[0]
    mock_get_used_disks.return_value = load_cmd_json_fixture[1]

    unused_disks = await list_unused_disks(1000)

    expected_return = [
        {'name': 'sdc', 'size': 250059350016, 'mounted': False}, 
        {'name': 'sdd', 'size': 250059350016, 'mounted': False}
    ]
    assert unused_disks == expected_return


@patch("app.core.disk_management.run_command")
def test_get_disk_json_error_code(mock_run_command):
    mock_run_command.return_value = (1, "Generic Error")

    with pytest.raises(Exception) as e:
        _get_disk_json(1000)

    assert "Generic Error" in str(e.value)
