import pytest
from pathlib import Path

from app.utils.sanitise import sanitise_username, sanitise_path
from app.core.errors import InvalidUsernameFormatError

def test_sanitise_username():
    valid_usernames = [
        "valid", " valid", "Valid", "_valid", "valid99"
    ]

    for username in valid_usernames:
        sanitised_username = sanitise_username(username)
        assert sanitised_username == username.strip().lower()


def test_sanitise_username_invalid():
    invalid_usernames = [
        "", "1test", "-test", "user name", "user.name", "user@name", "test$"
        "a_this_string_is_exactly_thirty_three_characters", "9", "-"
    ]

    for username in invalid_usernames:
        with pytest.raises(InvalidUsernameFormatError):
            a = sanitise_username(username)


@pytest.mark.parametrize(
    "input_path, expected_type, expected_str",
    [
        ("./file.txt", str, str(Path.cwd() / "file.txt")),
        (Path("./file.txt"), Path, str(Path.cwd() / "file.txt")),
        ("/usr/local/../bin", str, "/usr/bin"),
        ("~/documents", str, str(Path.home() / "documents")),
        ("/tmp/test\x00file.txt", str, "/tmp/testfile.txt"),
    ],
)
def test_sanitise_path(input_path, expected_type, expected_str):
    result = sanitise_path(input_path)
    
    assert isinstance(result, expected_type)
    assert str(result) == expected_str


def test_sanitise_path_invalid_type():
    with pytest.raises(TypeError):
        sanitise_path(123)