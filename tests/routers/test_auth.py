import pytest
from unittest.mock import MagicMock, patch

from app.core.security import COOKIE_NAME
from app.core.errors import InvalidCredentialsError, InvalidUsernameFormatError


def test_read_login(client):
    response = client.get('/login', follow_redirects=False)
    assert response.status_code == 200


def test_read_login_authenticated(authenticated_client):
    response = authenticated_client.get('/login', follow_redirects=False)
    assert response.status_code == 303


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


def test_post_logout_unauthenticated(client):
    client.cookies.clear() 

    response = client.post('/logout', follow_redirects=False)
    
    assert response.status_code == 307
    assert response.headers["Location"] == "/login"
    

def test_logout_authenticated(authenticated_client):
    response = authenticated_client.post('/logout', follow_redirects=False)
    
    assert response.status_code == 303
    assert response.headers["Location"] == "/login"
