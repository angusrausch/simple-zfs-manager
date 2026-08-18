import pytest
from pathlib import Path

from app.core.system.file_mod import verify_file_integrity


def test_file_verification(create_lock_dir):
    test_file_path = create_lock_dir / "test_file_verification"
    test_lock_file_path = create_lock_dir / test_file_path.relative_to(test_file_path.anchor)
    
    with open(test_file_path, 'w') as test_file:
        test_file.write("this should match")

    test_lock_file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(test_lock_file_path, 'w') as test_lock_file:
        test_lock_file.write("this should match")

    assert verify_file_integrity(test_file_path) == True


def test_file_verification_no_match(create_lock_dir):
    test_file_path = create_lock_dir / "test_file_verification_no_match"
    test_lock_file_path = create_lock_dir / test_file_path.relative_to(test_file_path.anchor)
    
    with open(test_file_path, 'w') as test_file:
        test_file.write("this should not match")

    test_lock_file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(test_lock_file_path, 'w') as test_lock_file:
        test_lock_file.write("this should really not match")

    assert verify_file_integrity(test_file_path) == False


def test_file_verification_create_file(create_lock_dir, caplog):
    test_file_path = create_lock_dir / "test_file_verification_create_file"
    test_lock_file_path = create_lock_dir / test_file_path.relative_to(test_file_path.anchor)
    
    with open(test_file_path, 'w') as test_file:
        test_file.write("this should match")

    assert not test_lock_file_path.exists()

    assert verify_file_integrity(test_file_path) == True # Makes the file
    
    assert f"[FILE] New lock file at {test_lock_file_path}" in caplog.text
    
    assert test_lock_file_path.is_file()
    
    assert verify_file_integrity(test_file_path) == True # Checks the file matches


def test_file_verification_folder_exists(create_lock_dir, caplog):
    test_file_path = create_lock_dir / "test_file_verification_folder_exists"
    test_lock_file_path = create_lock_dir / test_file_path.relative_to(test_file_path.anchor)
    
    with open(test_file_path, 'w') as test_file:
        test_file.write("this should match")
    
    test_lock_file_path.mkdir(parents=True)

    with pytest.raises(FileExistsError) as e:
        verify_file_integrity(test_file_path)
    
    assert f"Folder exists at {test_lock_file_path}, this should be a file" in str(e.value)
    
    assert f"[FILE] File verification found folder exists at {test_lock_file_path}, this should be a file" in caplog.text


def test_file_verification_input_not_exist(create_lock_dir, caplog):
    test_file_path = create_lock_dir / "test_file_verification_input_not_exist"
    
    with pytest.raises(FileNotFoundError) as e:
        verify_file_integrity(test_file_path)
    
    assert f"Input file does not exist: {test_file_path}" in str(e.value)
    
    assert f"[FILE] File Verification found input file does not exist: {test_file_path}" in caplog.text

