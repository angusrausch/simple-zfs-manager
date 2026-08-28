import pytest
from unittest.mock import patch
from pathlib import Path

from app.core.smb.smb import list_shares
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