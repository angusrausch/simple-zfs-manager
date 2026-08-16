import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import get_current_user

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def authenticated_client(client):
    async def mock_get_current_user():
        return 1000

    app.dependency_overrides[get_current_user] = mock_get_current_user

    async def mock_user_logged_in_true(*args, **kwargs):
        return True

    with patch("app.routers.auth.user_logged_in", new=mock_user_logged_in_true):
        yield client

    app.dependency_overrides.clear()