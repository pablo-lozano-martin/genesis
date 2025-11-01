# ABOUTME: Secure temporary file handling with guaranteed cleanup
# ABOUTME: Provides context manager for audio file storage with secure permissions

import tempfile
import os
from pathlib import Path
from uuid import uuid4
from contextlib import contextmanager


@contextmanager
def secure_temp_file(suffix: str = ".webm"):
    """
    Context manager for secure temporary file handling.
    - Creates file in OS temp directory
    - Sets secure permissions (600)
    - Generates random filename
    - Guarantees cleanup on exit
    """
    temp_dir = tempfile.gettempdir()
    filename = f"{uuid4().hex}{suffix}"
    filepath = Path(temp_dir) / filename

    try:
        # Create file with secure permissions (owner read/write only)
        filepath.touch(mode=0o600)
        yield filepath
    finally:
        # Secure delete: overwrite before deletion
        if filepath.exists():
            try:
                size = filepath.stat().st_size
                filepath.write_bytes(os.urandom(size))
            except:
                pass
            filepath.unlink()
