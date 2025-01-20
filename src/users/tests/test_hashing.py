import pytest
from users.domain.interfaces import BaseHasherI
from users.hashing import BcryptHasher, SHA256Hasher


@pytest.mark.parametrize("hasher", [BcryptHasher(), SHA256Hasher()])
def test_hash(hasher: BaseHasherI):
    password = "test123"
    hashed_password = hasher.hash(password)
    try:
        assert hashed_password.decode() != password
    except UnicodeDecodeError:
        pass


@pytest.mark.parametrize("hasher", [BcryptHasher(), SHA256Hasher()])
def test_compare(hasher: BaseHasherI):
    password = "test123"
    hashed_password = hasher.hash(password)
    assert hasher.compare(password, hashed_password)
