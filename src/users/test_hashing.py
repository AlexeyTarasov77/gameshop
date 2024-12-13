import pytest

from users.domain.interfaces import HasherI
from users.hashing import BcryptHasher


@pytest.fixture
def hasher() -> HasherI:
    return BcryptHasher()


def test_hash(hasher: HasherI):
    password = "test123"
    hashed_password = hasher.hash(password)
    assert hashed_password.decode() != password
    assert len(hashed_password) == 60


def test_compare(hasher: HasherI):
    password = "test123"
    hashed_password = hasher.hash(password)
    assert hasher.compare(password, hashed_password)
