import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone
from fastapi import Request, HTTPException, status

from app.core.security import COOKIE_NAME, user_logged_in, create_token, create_login_token, get_current_user, _decode_token
from app.core.errors import InvalidCredentialsError

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

    token = await create_login_token("validuser", "correctpassword")
    uid = await _decode_token(token)

    assert uid == 1001
    mock_pam_instance.authenticate.assert_called_once_with("validuser", "correctpassword")
    mock_getpwnam.assert_called_once_with("validuser")


@pytest.mark.asyncio
@patch("app.core.system.pam_auth.pam.pam")
async def test_failed_authentication(mock_pam_class):
    mock_pam_instance = MagicMock()
    mock_pam_instance.authenticate.return_value = False
    mock_pam_class.return_value = mock_pam_instance

    with pytest.raises(InvalidCredentialsError) as exc_info:
        await create_login_token("validuser", "wrongpassword")

    assert "Incorrect username or password" in str(exc_info.value)


@pytest.mark.asyncio
@patch("app.core.system.pam_auth.pwd.getpwnam")
@patch("app.core.system.pam_auth.pam.pam")
async def test_pam_succeeds_but_user_missing_in_pwd(mock_pam_class, mock_getpwnam):
    mock_pam_instance = MagicMock()
    mock_pam_instance.authenticate.return_value = True
    mock_pam_class.return_value = mock_pam_instance
    
    mock_getpwnam.side_effect = KeyError("user not found")

    with pytest.raises(InvalidCredentialsError) as exc_info:
        await create_login_token("weirduser", "password")

    assert "Incorrect username or password" in str(exc_info.value)


@pytest.mark.asyncio
@patch("app.core.security._decode_token")
async def test_get_current_user_valid_token(mock_decode):
    mock_decode.return_value = 1001
    
    scope = {
        "type": "http",
        "headers": [(b"cookie", f"{COOKIE_NAME}=valid_jwt_string_here".encode())]
    }
    req = Request(scope)
    
    result = await get_current_user(req)
    
    assert result == 1001
    mock_decode.assert_awaited_once_with("valid_jwt_string_here")


@pytest.mark.asyncio
@patch("app.core.security._decode_token")
async def test_get_current_user_missing_or_invalid_token(mock_decode):
    mock_decode.return_value = None
    
    scope = {"type": "http", "headers": []}
    req = Request(scope)
    
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(req)
        
    assert exc_info.value.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert exc_info.value.headers["Location"] == "/login"


@pytest.mark.asyncio
@patch("app.core.security._decode_token")
async def test_get_user_logged_in_valid_token(mock_decode):
    mock_decode.return_value = 1001
    
    scope = {
        "type": "http",
        "headers": [(b"cookie", f"{COOKIE_NAME}=valid_token".encode())]
    }
    req = Request(scope)
    
    result = await user_logged_in(req)
    
    assert result == True
    mock_decode.assert_awaited_once_with("valid_token")


@pytest.mark.asyncio
@patch("app.core.security._decode_token")
async def test_get_user_logged_in_missing_or_invalid_token(mock_decode):
    mock_decode.return_value = None
    
    scope = {
        "type": "http",
        "headers": [(b"cookie", f"{COOKIE_NAME}=invalid_token".encode())]
    }
    req = Request(scope)
    
    result = await user_logged_in(req)
    
    assert result == False
    mock_decode.assert_awaited_once_with("invalid_token")


@pytest.mark.asyncio
async def test_get_user_logged_in_expired_token():
    past_time = datetime.now(timezone.utc) - timedelta(hours=4)
    
    with patch("app.core.security.datetime") as mock_datetime:
        mock_datetime.now.return_value = past_time
        expired_token = create_token(1000)
    
    scope = {
        "type": "http",
        "headers": [(b"cookie", f"{COOKIE_NAME}={expired_token}".encode())]
    }
    req = Request(scope)
    
    result = await user_logged_in(req)
    
    assert result == False


@pytest.mark.asyncio
async def test_get_user_logged_in_empty_uid_token():
    token = create_token("")
    
    scope = {
        "type": "http",
        "headers": [(b"cookie", f"{COOKIE_NAME}={token}".encode())]
    }
    req = Request(scope)
    
    result = await user_logged_in(req)
    
    assert result == False
