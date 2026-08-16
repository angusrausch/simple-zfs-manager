import pytest

from app.utils.sanitise import sanitise_username
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