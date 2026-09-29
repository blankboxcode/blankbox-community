"""Cross-platform exclusion for Core and stopped-catalog maintenance."""
import os
from pathlib import Path
from file_safety import reject_links


class RuntimeLock:
    def __init__(self, data):
        directory = reject_links(data)
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = reject_links(directory / '.blankbox-runtime.lock')
        fd = os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        self.stream = os.fdopen(fd, 'r+b')
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            self.stream.close()
            raise ValueError('Stop Blank Box before changing this catalog; another process holds it.') from error

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.stream.close()
