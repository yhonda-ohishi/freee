"""
freeeログをGoogle Driveにバックアップ（PostToolUseフック用）

rclone で logs/ を gdrive:freee-logs/ に同期する。
"""

import subprocess
import sys
import os
from pathlib import Path

RCLONE = os.path.expanduser("~/bin/rclone.exe")
LOGS_DIR = "c:/freee/logs"
REMOTE = "gdrive:freee-logs"


def main():
    if not Path(RCLONE).exists():
        return

    if not Path(LOGS_DIR).exists():
        return

    try:
        subprocess.run(
            [RCLONE, "sync", LOGS_DIR, REMOTE, "--quiet"],
            timeout=30,
            capture_output=True,
        )
    except Exception:
        pass


if __name__ == "__main__":
    main()
