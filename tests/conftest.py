import pytest
import os
import sys
import shutil
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient

current_dir = Path.cwd()
sys.path.insert(0, str(current_dir))
log_location = current_dir / "tests/log/app.log"
os.environ["LOG_LOCATION"] = str(log_location)
lock_file_path = current_dir / "tests/lock-tests/lock"
os.environ["LOCK_FILE_PATH"] = str(lock_file_path)

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


@pytest.fixture(scope="session")
def create_log_dir():
    log_location.parent.mkdir(exist_ok=True)
    yield
    shutil.rmtree(log_location.parent)


@pytest.fixture(scope="function")
def create_lock_dir():
    lock_file_path.mkdir(parents=True, exist_ok=True)
    yield lock_file_path.parent
    shutil.rmtree(lock_file_path.parent)


@pytest.fixture
def load_cmd_json_fixture(request):
    test_dir = Path(request.module.__file__).parent
    
    test_name = request.node.name.replace("/", "_")
    
    fixture_dir = fixture_path = test_dir / "test_returns"

    if (fixture_dir / f"{test_name}.json").exists():
        return (fixture_dir / f"{test_name}.json").read_text(encoding="utf-8")
    elif (fixture_dir / f"{test_name}.txt").exists():
        return (fixture_dir / f"{test_name}.txt").read_text(encoding="utf-8")
    elif (fixture_dir / f"{test_name}.py").exists():
        source = (fixture_dir / f"{test_name}.py").read_text(encoding="utf-8")
        local_vars = {}
        try:
            exec(source, globals(), local_vars) 
        except Exception as e:
            pytest.fail(f"Error executing Python fixture {test_name}: {e}")
        if "value" in local_vars:
            return local_vars["value"]
        else:
            pytest.fail(f"Python fixture found, but 'value' variable is missing in: {test_name}")
    else:
        pytest.fail(f"Missing expected test fixture file at: {fixture_path}")
