import base64


def is_base64(s: str) -> bool:
    try:
        return base64.b64encode(base64.b64decode(s)).decode() == s
    except Exception:
        return False
