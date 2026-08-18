import logging
import pytest
from app.core.system.runner import run_command

TEST_UID = 100

def test_command_runs(caplog):
    command = ["ls", "-l"]

    with caplog.at_level(logging.INFO, logger="app.audit"):
        return_code, output = run_command(TEST_UID, command)

    assert return_code == 0
    assert f"[CMD] User {TEST_UID} requested command:" in caplog.text
    assert f"Command succeeded for User {TEST_UID}" in caplog.text


def test_command_fails(caplog):
    command = ["ls", "--this-flag-does-not-exist"]

    with caplog.at_level(logging.INFO, logger="app.audit"):
        return_code, output = run_command(TEST_UID, command)

    assert return_code == 2
    assert f"[CMD] User {TEST_UID} requested command:" in caplog.text
    assert f"[CMD] Command failed for User {TEST_UID} | Code: {return_code} | Error: {output}" in caplog.text
    

def test_command_timeout(caplog):
    command = ["sleep", "5"]
    timeout = 0.01

    with caplog.at_level(logging.INFO, logger="app.audit"):
        return_code, output = run_command(TEST_UID, command, timeout=timeout)

    assert return_code == -1
    assert f"[CMD] User {TEST_UID} requested command:" in caplog.text
    assert f"[CMD] Command timed out for User {TEST_UID} after {timeout}s." in caplog.text


def test_command_not_exists(caplog):
    command = ["invalid-path"]

    with caplog.at_level(logging.INFO, logger="app.audit"):
        return_code, output = run_command(TEST_UID, command)

    assert return_code == -2
    assert f"[CMD] Failed to execute binary for User {TEST_UID} | Error: {output}" in caplog.text