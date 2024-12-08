import bcrypt


class BcryptHasher:
    def hash(self, password: str) -> bytes:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode(), salt)

    def compare(self, password: str, hashed_password: bytes) -> bool:
        return bcrypt.checkpw(password.encode(), hashed_password)
