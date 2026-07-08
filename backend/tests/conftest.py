"""Point the app at an isolated temp DB/storage before anything imports settings."""

import os
import tempfile
from pathlib import Path

_tmp = Path(tempfile.mkdtemp(prefix="revoice-test-"))
os.environ["REVOICE_DATABASE_URL"] = f"sqlite:///{(_tmp / 'test.db').as_posix()}"
os.environ["REVOICE_STORAGE_DIR"] = str(_tmp / "storage")
os.environ["REVOICE_ENGINE"] = "mock"
