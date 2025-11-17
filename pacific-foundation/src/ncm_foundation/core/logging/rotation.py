"""
Log rotation implementation.
"""

import asyncio
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

from .interfaces import LogRotator


class SizeBasedRotator(LogRotator):
    """Size-based log rotator."""

    def __init__(self, max_size: int):
        self.max_size = max_size

    async def should_rotate(self, file_path: str) -> bool:
        """Check if file should be rotated based on size."""
        try:
            if not os.path.exists(file_path):
                return False

            file_size = os.path.getsize(file_path)
            return file_size >= self.max_size

        except Exception:
            return False

    async def rotate(self, file_path: str) -> str:
        """Rotate log file based on size."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            rotated_path = f"{file_path}.{timestamp}"

            shutil.move(file_path, rotated_path)

            # Create new empty file
            Path(file_path).touch()

            return rotated_path

        except Exception as e:
            raise RuntimeError(f"Failed to rotate log file: {e}")

    async def cleanup_old_files(self, file_path: str, max_files: int) -> None:
        """Clean up old log files."""
        try:
            base_path = Path(file_path)
            directory = base_path.parent
            pattern = f"{base_path.name}.*"

            # Find all rotated files
            rotated_files = []
            for file in directory.glob(pattern):
                if file.name != base_path.name:
                    rotated_files.append(file)

            # Sort by modification time (oldest first)
            rotated_files.sort(key=lambda f: f.stat().st_mtime)

            # Remove excess files
            if len(rotated_files) > max_files:
                for file in rotated_files[:-max_files]:
                    file.unlink()

        except Exception as e:
            raise RuntimeError(f"Failed to cleanup old log files: {e}")


class TimeBasedRotator(LogRotator):
    """Time-based log rotator."""

    def __init__(self, interval: str):
        self.interval = interval
        self._intervals = {
            "daily": timedelta(days=1),
            "weekly": timedelta(weeks=1),
            "monthly": timedelta(days=30),
        }

    async def should_rotate(self, file_path: str) -> bool:
        """Check if file should be rotated based on time."""
        try:
            if not os.path.exists(file_path):
                return False

            file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
            now = datetime.now()

            if self.interval == "daily":
                return file_mtime.date() < now.date()
            elif self.interval == "weekly":
                return (now - file_mtime).days >= 7
            elif self.interval == "monthly":
                return (now - file_mtime).days >= 30

            return False

        except Exception:
            return False

    async def rotate(self, file_path: str) -> str:
        """Rotate log file based on time."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            rotated_path = f"{file_path}.{timestamp}"

            shutil.move(file_path, rotated_path)

            # Create new empty file
            Path(file_path).touch()

            return rotated_path

        except Exception as e:
            raise RuntimeError(f"Failed to rotate log file: {e}")

    async def cleanup_old_files(self, file_path: str, max_files: int) -> None:
        """Clean up old log files."""
        try:
            base_path = Path(file_path)
            directory = base_path.parent
            pattern = f"{base_path.name}.*"

            # Find all rotated files
            rotated_files = []
            for file in directory.glob(pattern):
                if file.name != base_path.name:
                    rotated_files.append(file)

            # Sort by modification time (oldest first)
            rotated_files.sort(key=lambda f: f.stat().st_mtime)

            # Remove excess files
            if len(rotated_files) > max_files:
                for file in rotated_files[:-max_files]:
                    file.unlink()

        except Exception as e:
            raise RuntimeError(f"Failed to cleanup old log files: {e}")


class LogRotator:
    """Main log rotator coordinator."""

    def __init__(self, rotators: List[LogRotator]):
        self.rotators = rotators

    async def should_rotate(self, file_path: str) -> bool:
        """Check if any rotator wants to rotate."""
        for rotator in self.rotators:
            if await rotator.should_rotate(file_path):
                return True
        return False

    async def rotate(self, file_path: str) -> str:
        """Rotate using the first applicable rotator."""
        for rotator in self.rotators:
            if await rotator.should_rotate(file_path):
                return await rotator.rotate(file_path)

        raise RuntimeError("No rotator applicable")

    async def cleanup_old_files(self, file_path: str, max_files: int) -> None:
        """Clean up old files using all rotators."""
        for rotator in self.rotators:
            try:
                await rotator.cleanup_old_files(file_path, max_files)
            except Exception as e:
                # Log error but continue with other rotators
                print(f"Rotator cleanup error: {e}")
