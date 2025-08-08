"""Input/output directory helpers with optional Google Drive support."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

DEFAULT_LOCAL_ROOT = Path("/content")
DEFAULT_DRIVE_ROOT = Path("/content/drive/MyDrive")
REQUIRED_FREE_BYTES = 100 * 1024 * 1024  # 100 MB


def _has_rw(path: Path) -> bool:
    return os.access(path, os.R_OK | os.W_OK)


def resolve_input_path(path: str | Path) -> Path:
    """Resolve an input directory path and ensure read/write access."""
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"{p} not found")
    if not _has_rw(p):
        raise PermissionError(f"No read/write access to {p}")
    return p


def resolve_output_path(path: str | Path, required_bytes: int = REQUIRED_FREE_BYTES) -> Path:
    """Resolve an output directory path, ensuring it exists and has space."""
    p = Path(path).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    if not _has_rw(p):
        raise PermissionError(f"No read/write access to {p}")
    _total, _used, free = shutil.disk_usage(p)
    if free < required_bytes:
        raise OSError(f"Not enough free space in {p}: {free} bytes available")
    return p


def _mount_or_local() -> Path:
    """Try to mount Google Drive; fall back to local /content."""
    try:
        from google.colab import drive  # type: ignore

        if not DEFAULT_DRIVE_ROOT.exists():
            drive.mount(str(DEFAULT_DRIVE_ROOT.parent))
        if DEFAULT_DRIVE_ROOT.exists():
            return DEFAULT_DRIVE_ROOT
    except Exception:
        pass
    return DEFAULT_LOCAL_ROOT


def get_default_io(required_bytes: int = REQUIRED_FREE_BYTES) -> tuple[Path, Path]:
    """Return default input/output directories with checks."""
    base = _mount_or_local()
    input_dir = resolve_output_path(base / "input", required_bytes)
    output_dir = resolve_output_path(base / "output", required_bytes)
    return input_dir, output_dir
