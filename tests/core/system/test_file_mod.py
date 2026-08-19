import pytest
from pathlib import Path
import os
import stat
from unittest.mock import patch, mock_open

from app.core.system.file_mod import verify_file_integrity, _safe_write, write_file, _find_lock_path
from app.core.errors import MissingInputFileError, LockFileMismatchError, LockPathBlockedError, PathBlockedError, CannotWriteError


def test_file_verification(create_lock_dir):
    test_file_path = create_lock_dir / "test_file_verification"
    test_lock_file_path = _find_lock_path(test_file_path)
    
    with open(test_file_path, 'w') as test_file:
        test_file.write("this should match")

    test_lock_file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(test_lock_file_path, 'w') as test_lock_file:
        test_lock_file.write("this should match")

    verify_file_integrity(test_file_path)


def test_file_verification_no_match(create_lock_dir, caplog):
    test_file_path = create_lock_dir / "test_file_verification_no_match"
    test_lock_file_path = _find_lock_path(test_file_path)

    with open(test_file_path, 'w') as test_file:
        test_file.write("this should not match")

    test_lock_file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(test_lock_file_path, 'w') as test_lock_file:
        test_lock_file.write("this should really not match")

    with pytest.raises(LockFileMismatchError) as e:
        verify_file_integrity(test_file_path)

    assert f"File verification failed on file {test_file_path}" in str(e.value)
    
    assert f"File verification failed on file {test_file_path}" in caplog.text


def test_file_verification_create_file(create_lock_dir, caplog):
    test_file_path = create_lock_dir / "test_file_verification_create_file"
    test_lock_file_path = _find_lock_path(test_file_path)
    
    with open(test_file_path, 'w') as test_file:
        test_file.write("this should match")

    assert not test_lock_file_path.exists()

    verify_file_integrity(test_file_path) # Makes the file
    
    assert f"[FILE] New lock file at {test_lock_file_path}" in caplog.text
    
    assert test_lock_file_path.is_file()
    
    verify_file_integrity(test_file_path) # Checks the file matches


def test_file_verification_folder_exists(create_lock_dir, caplog):
    test_file_path = create_lock_dir / "test_file_verification_folder_exists"
    test_lock_file_path = _find_lock_path(test_file_path)
    
    with open(test_file_path, 'w') as test_file:
        test_file.write("this should match")
    
    test_lock_file_path.mkdir(parents=True)

    with pytest.raises(LockPathBlockedError) as e:
        verify_file_integrity(test_file_path)
    
    assert f"File verification found folder exists at {test_lock_file_path}, this should be a file" in str(e.value)
    
    assert f"[FILE] File verification found folder exists at {test_lock_file_path}, this should be a file" in caplog.text


def test_file_verification_input_not_exist(create_lock_dir, caplog):
    test_file_path = create_lock_dir / "test_file_verification_input_not_exist"
    
    with pytest.raises(MissingInputFileError) as e:
        verify_file_integrity(test_file_path)
    
    assert f"File Verification found input file does not exist: {test_file_path}" in str(e.value)
    
    assert f"[FILE] File Verification found input file does not exist: {test_file_path}" in caplog.text


def test_safe_write(tmp_path):
    test_file_path = tmp_path / "test_safe_write"
    test_file_contents = "this is in file"

    _safe_write(test_file_path, test_file_contents)

    with open(test_file_path, 'r', encoding="utf-8") as test_file:
        assert test_file_contents in test_file.read()


def test_safe_write_new_dir(tmp_path):
    test_file_path = tmp_path / "dir/test_safe_write"
    test_file_contents = "this is in file"

    _safe_write(test_file_path, test_file_contents)

    with open(test_file_path, 'r', encoding="utf-8") as test_file:
        assert test_file_contents in test_file.read()


@patch("builtins.open", new_callable=mock_open)
@patch("os.fsync")
def test_safe_write_data_phase_failure_cleans_up(mock_fsync, mock_file_open, tmp_path):
    mock_fsync.side_effect = OSError(28, "No space left on device")
    
    target_file = tmp_path / "test.txt"
    shadow_file = tmp_path / ".test.txt.shadow"
    
    shadow_file.touch()
    
    with pytest.raises(OSError):
        _safe_write(target_file, "won't be in file ")
        
    assert not shadow_file.exists()


@patch("pathlib.Path.replace")
def test_safe_write_metadata_phase_failure(mock_replace, tmp_path):
    mock_replace.side_effect = PermissionError("Rename forbidden")
    
    target_file = tmp_path / "test.txt"
    
    with pytest.raises(PermissionError):
        _safe_write(target_file, "some data")


def test_write_file(create_lock_dir):
    test_file_path = create_lock_dir / "test_write_file"
    contents = "this should be in file"

    write_file(test_file_path, contents)

    with open(test_file_path, 'r', encoding="utf-8") as test_file:
        assert contents in test_file.read() 

    verify_file_integrity(test_file_path)


def test_write_file_previous_file(create_lock_dir):
    test_file_path = create_lock_dir / "test_write_file_previous_file"
    old_contents = "this used to be in file"

    with open(test_file_path, 'w', encoding="utf-8") as test_file:
        test_file.write(old_contents)

    new_contents = "this is now in the file"

    write_file(test_file_path, new_contents)

    with open(test_file_path, 'r', encoding="utf-8") as test_file:
        file_contents = test_file.read() 

    assert old_contents not in file_contents
    assert new_contents in file_contents

    verify_file_integrity(test_file_path)


def test_write_file_folder_exists(create_lock_dir, caplog):
    test_file_path = create_lock_dir / "test_write_file_folder_exists"

    test_file_path.mkdir(parents=True)

    with pytest.raises(PathBlockedError) as e:
        write_file(test_file_path, "")

    assert f"File write found folder exists at {test_file_path}, this should be a file" in str(e.value)

    assert f"[FILE] File write found folder exists at {test_file_path}, this should be a file" in caplog.text


def test_write_file_cannot_write_lock_file_file_exists(create_lock_dir, caplog):
    test_file_path = create_lock_dir / "locked/test_write_file_cannot_write_lock_file_file_exists"
    test_lock_file_path = _find_lock_path(test_file_path)
    old_contents = "this used to be in file"

    write_file(test_file_path, old_contents)

    lock_dir = test_lock_file_path.parent
    os.chmod(lock_dir, stat.S_IRUSR | stat.S_IXUSR)

    new_contents = "this is now in the file"

    try:
        with pytest.raises(CannotWriteError) as e:
            write_file(test_file_path, new_contents)
        
        with open(test_file_path, 'r', encoding="utf-8") as test_file:
            file_contents = test_file.read()

        assert old_contents in file_contents
        assert new_contents not in file_contents

        assert f"[FILE] Failed to write file {test_lock_file_path}" in caplog.text
    finally:
        os.chmod(lock_dir, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)


def test_write_file_cannot_write_lock_file(create_lock_dir, caplog):
    test_file_path = create_lock_dir / "locked/test_write_file_cannot_write_lock_file"
    test_lock_file_path = _find_lock_path(test_file_path)

    lock_dir = test_lock_file_path.parent
    lock_dir.mkdir(exist_ok=True, parents=True)
    test_lock_file_path.touch()
    os.chmod(lock_dir, stat.S_IRUSR | stat.S_IXUSR)

    new_contents = "this is in the file"

    try:
        with pytest.raises(CannotWriteError) as e:
            write_file(test_file_path, new_contents)
        
        assert not test_file_path.exists()

        assert f"[FILE] Failed to write file {test_lock_file_path}" in caplog.text
    finally:
        os.chmod(lock_dir, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)


def test_write_file_cannot_write_lock_file_folder_exists(create_lock_dir, caplog):
    test_file_path = create_lock_dir / "test_write_file_cannot_write_lock_file_folder_exists"
    test_lock_file_path = _find_lock_path(test_file_path)

    test_lock_file_path.mkdir(parents=True, exist_ok=True)

    new_contents = "this is in the file"

    with pytest.raises(CannotWriteError) as e:
        write_file(test_file_path, new_contents)
        
        assert not test_file_path.exists()

        assert f"[FILE] Failed to write file {test_lock_file_path}" in caplog.text


def test_write_file_cannot_write_file_file_exists(create_lock_dir, caplog):
    test_file_path = create_lock_dir / "locked/test_write_file_cannot_write_file_file_exists"
    test_lock_file_path = _find_lock_path(test_file_path)
    old_contents = "this used to be in file"

    write_file(test_file_path, old_contents)

    file_dir = test_file_path.parent
    os.chmod(file_dir, stat.S_IRUSR | stat.S_IXUSR)

    new_contents = "this is now in the file"

    try:
        with pytest.raises(CannotWriteError) as e:
            write_file(test_file_path, new_contents)
        
        with open(test_file_path, 'r', encoding="utf-8") as test_file:
            file_contents = test_file.read()

        assert old_contents in file_contents
        assert new_contents not in file_contents

        assert f"[FILE] Failed to write file {test_file_path}" in caplog.text
    finally:
        os.chmod(file_dir, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)


def test_write_file_cannot_write_file(create_lock_dir, caplog):
    test_file_path = create_lock_dir / "locked/test_write_file_cannot_write_file"
    test_lock_file_path = _find_lock_path(test_file_path)

    file_dir = test_file_path.parent
    file_dir.mkdir(exist_ok=True, parents=True)
    test_file_path.touch()
    os.chmod(file_dir, stat.S_IRUSR | stat.S_IXUSR)

    new_contents = "this is not in the file"

    try:
        with pytest.raises(CannotWriteError) as e:
            write_file(test_file_path, new_contents)
        
        with open(test_file_path, 'r', encoding="utf-8") as test_file:
            assert "this is not in the file" not in test_file.read()

        assert f"[FILE] Failed to write file {test_file_path}" in caplog.text
    finally:
        os.chmod(file_dir, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)


def test_write_file_cannot_write_file_folder_exists(create_lock_dir, caplog):
    test_file_path = create_lock_dir / "test_write_file_cannot_write_file_folder_exists"
    test_lock_file_path = _find_lock_path(test_file_path)

    test_file_path.mkdir(parents=True, exist_ok=True)

    new_contents = "this is in the file"

    with pytest.raises(PathBlockedError) as e:
        write_file(test_file_path, new_contents)
        
        assert not test_file_path.exists()

        assert f"[FILE] Failed to write file {test_file_path}" in caplog.text


def test_write_file_previous_file_change_contents(create_lock_dir, caplog):
    test_file_path = create_lock_dir / "test_write_file_previous_file"
    old_contents = "this used to be in file"

    write_file(test_file_path, old_contents)

    incorrect_contents = "this shouldn't be in file"
    with open(test_file_path, 'w', encoding="utf-8") as test_file:
        test_file.write(incorrect_contents)

    new_contents = "this is now in the file"

    with pytest.raises(LockFileMismatchError) as e:
        write_file(test_file_path, new_contents)

    assert f"File verification failed on file {test_file_path}" in str(e.value)

    assert f"File verification failed on file {test_file_path}" in caplog.text
