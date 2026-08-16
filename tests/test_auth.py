import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from app.core.system.pam_auth import get_authenticated_uid
from app.core.security import COOKIE_NAME, user_logged_in
from app.core.errors import InvalidCredentialsError, InvalidUsernameFormatError

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

    with pytest.raises(InvalidCredentialsError) as exc_info:
        await get_authenticated_uid("validuser", "wrongpassword")

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
        await get_authenticated_uid("weirduser", "password")

    assert "Incorrect username or password" in str(exc_info.value)


def test_read_login(client):
    response = client.get('/login', follow_redirects=False)
    assert response.status_code == 200


def test_post_login_success(client):
    with patch("app.core.system.pam_auth.pam.pam") as mock_pam_class, \
         patch("app.core.system.pam_auth.pwd.getpwnam") as mock_getpwnam:
        
        mock_pam_instance = MagicMock()
        mock_pam_instance.authenticate.return_value = True
        mock_pam_class.return_value = mock_pam_instance
        
        mock_user_entry = MagicMock()
        mock_user_entry.pw_uid = 1001
        mock_getpwnam.return_value = mock_user_entry

        payload = {
            'username': 'validuser',
            'password': 'correctpassword'
        }

        response = client.post('/login', data=payload, follow_redirects=False)
        
        assert response.status_code == 303
        assert response.headers["Location"] == "/"
        assert COOKIE_NAME in response.cookies


def test_post_login_fail_auth(client):
    with patch("app.core.system.pam_auth.pam.pam") as mock_pam_class, \
         patch("app.core.system.pam_auth.pwd.getpwnam") as mock_getpwnam:
        
        mock_pam_instance = MagicMock()
        mock_pam_instance.authenticate.return_value = False
        mock_pam_class.return_value = mock_pam_instance
        
        mock_user_entry = MagicMock()
        mock_user_entry.pw_uid = 1001
        mock_getpwnam.return_value = mock_user_entry

        payload = {
            'username': 'validuser',
            'password': 'wrongpassword'
        }

        response = client.post('/login', data=payload, follow_redirects=False)
        
        assert response.status_code == 401
        assert str(InvalidCredentialsError()) in response.text


def test_post_login_fail_format(client):
    payload = {
        'username': 'invaliduser/',
        'password': 'wrongpassword'
    }

    response = client.post('/login', data=payload, follow_redirects=False)
    
    assert response.status_code == 400
    assert str(InvalidUsernameFormatError()) in response.text
