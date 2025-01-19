import pytest
from users.domain.interfaces import HasherI
from users.hashing import BcryptHasher, SHA256Hasher


@pytest.mark.parametrize("hasher", [BcryptHasher(), SHA256Hasher()])
def test_hash(hasher: HasherI):
    password = "test123"
    hashed_password = hasher.hash(password)
    try:
        assert hashed_password.decode() != password
    except UnicodeDecodeError:
        pass


@pytest.mark.parametrize("hasher", [BcryptHasher(), SHA256Hasher()])
def test_compare(hasher: HasherI):
    password = "test123"
    hashed_password = hasher.hash(password)
    assert hasher.compare(password, hashed_password)
