"""One owner per data directory, including during backup restoration."""
import fcntl
import os
from pathlib import Path

class RunLock:
    def __init__(self, directory):
        directory = Path(directory)
        directory.mkdir(parents=True,exist_ok=True,mode=0o700)
        fd = os.open(str(directory/"server.lock"),os.O_CREAT|os.O_RDWR,0o600)
        self.file = os.fdopen(fd,"r+")
        try:
            fcntl.flock(self.file.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            self.file.close()
            raise RuntimeError("Songsketch is already using this data folder. Stop its server/background service before starting another instance or restoring.") from None
        self.file.seek(0)
        self.file.truncate()
        self.file.write(str(os.getpid()))
        self.file.flush()

    def close(self):
        if not self.file.closed:
            fcntl.flock(self.file.fileno(),fcntl.LOCK_UN)
            self.file.close()
