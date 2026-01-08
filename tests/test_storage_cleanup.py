import os
import time
from pathlib import Path
from tempfile import TemporaryDirectory

from face_blur.storage.cleanup import purge_old_files


def test_purge_old_files_removes_expired_files():
    with TemporaryDirectory() as temp_dir:
        storage_path = Path(temp_dir)
        old_file = storage_path / "old.jpg"
        new_file = storage_path / "new.jpg"

        old_file.write_bytes(b"old")
        new_file.write_bytes(b"new")

        old_time = time.time() - 3600
        os.utime(old_file, (old_time, old_time))

        removed = purge_old_files(storage_path, ttl_seconds=60)
        assert removed == 1
        assert not old_file.exists()
        assert new_file.exists()
