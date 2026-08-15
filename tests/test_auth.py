# tests/test_pam_auth.py
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from app.core.system.pam_auth import get_authenticated_uid

@pytest.mark.asyncio
@patch("app.core.system.pam_auth.pwd.getpwnam")
@patch("app.core.system.pam_auth.pam.pam")
async def test_successful_authentication(mock_pam_class, mock_getpwnam):
    mock_pam_instance = MagicMock()
    mock_pam_instance.authenticate.return_value = True
    mock_pam_class.return_value = mock_pam_instance
    
    mock_user_entry = MagicMock()
    mock_user_entry.pw_uid = 1001
    mock_getpwnam.return_value = mock_user_entry

    uid = await get_authenticated_uid("validuser", "correctpassword")

    assert uid == 1001
    mock_pam_instance.authenticate.assert_called_once_with("validuser", "correctpassword")
    mock_getpwnam.assert_called_once_with("validuser")


@pytest.mark.asyncio
@patch("app.core.system.pam_auth.pam.pam")
async def test_failed_authentication(mock_pam_class):
    mock_pam_instance = MagicMock()
    mock_pam_instance.authenticate.return_value = False
    mock_pam_class.return_value = mock_pam_instance

    with pytest.raises(HTTPException) as exc_info:
        await get_authenticated_uid("validuser", "wrongpassword")
        
    assert exc_info.value.status_code == 401
    assert "Authentication failed" in exc_info.value.detail


@pytest.mark.asyncio
@patch("app.core.system.pam_auth.pwd.getpwnam")
@patch("app.core.system.pam_auth.pam.pam")
async def test_pam_succeeds_but_user_missing_in_pwd(mock_pam_class, mock_getpwnam):
    mock_pam_instance = MagicMock()
    mock_pam_instance.authenticate.return_value = True
    mock_pam_class.return_value = mock_pam_instance
    
    mock_getpwnam.side_effect = KeyError("user not found")

    with pytest.raises(HTTPException) as exc_info:
        await get_authenticated_uid("weirduser", "password")

    assert exc_info.value.status_code == 401