from pathlib import Path
import sys

sys.path.append((Path().parent.parent / "src").absolute().as_posix())

import pytest
from contextlib import nullcontext as does_not_raise


def exc_to_ctx_manager(exc: type[Exception] | None):
    return pytest.raises(exc) if exc else does_not_raise()
