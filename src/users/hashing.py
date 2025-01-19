import bcrypt
from hashlib import sha256


class BcryptHasher:
    def hash(self, s: str) -> bytes:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(s.encode(), salt)

    def compare(self, s: str, hash: bytes) -> bool:
        return bcrypt.checkpw(s.encode(), hash)


class SHA256Hasher:
    def hash(self, s: str) -> bytes:
        return sha256(s.encode()).digest()

    def compare(self, s: str, hash: bytes) -> bool:
        return self.hash(s) == hash
