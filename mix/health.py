"""Environment health checks for audio mixing.

Provides utilities to verify required runtime dependencies such as GPU
memory, disk space, ffmpeg executable and audio sample rates.  Each check
returns an error string explaining the problem and a possible fix.  A
`run_preflight_checks` helper aggregates the individual checks.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import wave

try:  # pragma: no cover - optional dependency
    import torch  # type: ignore
except Exception:  # pragma: no cover
    torch = None  # type: ignore


def check_gpu(min_free_mb: int = 1024) -> str | None:
    """Validate that a CUDA device has at least ``min_free_mb`` free memory."""
    if not torch or not hasattr(torch, "cuda") or not torch.cuda.is_available():
        return (
            "CUDA GPU not available. Install a CUDA capable GPU or run on CPU."
        )
    try:
        free_bytes, _total = torch.cuda.mem_get_info()  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover - API may not exist
        return "Unable to determine GPU memory. Ensure recent PyTorch installation."
    free_mb = free_bytes / 1024**2
    if free_mb < min_free_mb:
        return (
            f"Insufficient GPU memory: {free_mb:.0f}MB available, "
            f"{min_free_mb}MB required. Close other applications or reduce batch size."
        )
    return None


def check_disk(path: str | Path, min_free_mb: int = 1024) -> str | None:
    """Ensure the filesystem containing ``path`` has enough free space."""
    usage = shutil.disk_usage(Path(path))
    free_mb = usage.free / 1024**2
    if free_mb < min_free_mb:
        return (
            f"Insufficient disk space at {path}: {free_mb:.0f}MB available, "
            f"{min_free_mb}MB required. Free up space or choose another location."
        )
    return None


def check_ffmpeg() -> str | None:
    """Verify that the ffmpeg executable is available on PATH."""
    if not shutil.which("ffmpeg"):
        return "ffmpeg executable not found. Install ffmpeg and ensure it is on PATH."
    return None


def check_sample_rate(input_dir: str | Path | None, expected_sr: int = 44100) -> str | None:
    """Confirm that all ``.wav`` files in ``input_dir`` have the expected sample rate."""
    if not input_dir:
        return None
    input_dir = Path(input_dir)
    errors = []
    for wav_path in input_dir.glob("*.wav"):
        with wave.open(str(wav_path), "rb") as wf:
            sr = wf.getframerate()
        if sr != expected_sr:
            errors.append(
                f"{wav_path.name} has sample rate {sr}Hz, expected {expected_sr}Hz."
            )
    if errors:
        return "; ".join(errors)
    return None


def check_model(model_path: str | Path | None) -> str | None:
    """Check that the optional model file exists."""
    if not model_path:
        return None
    model_path = Path(model_path)
    if not model_path.exists():
        return (
            f"Model file not found: {model_path}. Download the model or provide the correct path."
        )
    return None


def run_preflight_checks(
    input_dir: str | Path | None = None,
    output_dir: str | Path = ".",
    model_path: str | Path | None = None,
    expected_sr: int = 44100,
    min_gpu_mem_mb: int = 1024,
    min_disk_mb: int = 1024,
) -> list[str]:
    """Run all health checks and return a list of error messages."""
    errors = []
    gpu_err = check_gpu(min_gpu_mem_mb)
    if gpu_err:
        errors.append(gpu_err)
    disk_err = check_disk(output_dir, min_disk_mb)
    if disk_err:
        errors.append(disk_err)
    ffmpeg_err = check_ffmpeg()
    if ffmpeg_err:
        errors.append(ffmpeg_err)
    sr_err = check_sample_rate(input_dir, expected_sr)
    if sr_err:
        errors.append(sr_err)
    model_err = check_model(model_path)
    if model_err:
        errors.append(model_err)
    return errors
