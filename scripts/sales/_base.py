import sys
import os
from pathlib import Path

sys.path.append((Path().parent.parent / "src").absolute().as_posix())

from config import ConfigMode

if not os.environ.get("MODE"):
    os.environ["MODE"] = ConfigMode.LOCAL

from products.models import ProductPlatform


XBOX_REDIS_KEY = "parsed_xbox"
PSN_REDIS_KEY = "parsed_psn"
UPDATE_CHUNK_SIZE = 200


def get_redis_key_by_platform(platform: ProductPlatform):
    return {
        ProductPlatform.XBOX: XBOX_REDIS_KEY,
        ProductPlatform.PSN: PSN_REDIS_KEY,
    }[platform]
