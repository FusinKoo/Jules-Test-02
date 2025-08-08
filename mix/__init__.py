"""Minimal audio mixing library using only the Python standard library.

This module originally only provided utilities for loudness alignment and
mixdown.  The current iteration adds an **optional** source separation step
that can be toggled on or off by the caller.  The separation logic is heavily
simplified so it can run in constrained environments while still exposing a
high level API that mimics a real world system where different quality models
and hardware backends are available.

Key features
------------

* "Separation switch" – the caller decides whether to perform separation.
* "Model/quality levels" – ``low`` and ``high`` quality tiers.
* "CPU slow path / GPU fast path" – automatically choose a device when the
  caller does not specify one.
* Automatic degradation and bypass when resources are insufficient or when the
  separation step fails for any reason.

The actual separation algorithm implemented here is intentionally lightweight:
it merely copies the existing stems, acting as a placeholder for a real
separator.  This keeps the library dependency‑free while providing a clean
extension point for more advanced implementations.
"""
from pathlib import Path
import json
import wave
import array
import math
import os
import shutil
import time

TRACKS = ["vocals", "drums", "bass", "other"]


def _load(path):
    with wave.open(str(path), "rb") as wf:
        sr = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
        data = array.array("h", frames)
    # convert to float in [-1, 1]
    data = [s / 32768.0 for s in data]
    return data, sr


def _save(path, data, sr):
    path.parent.mkdir(parents=True, exist_ok=True)
    ints = array.array("h", [max(-32768, min(32767, int(x * 32767))) for x in data])
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(ints.tobytes())


def _rms_db(data):
    if not data:
        return -float("inf")
    rms = math.sqrt(sum(x * x for x in data) / len(data))
    if rms == 0:
        return -float("inf")
    return 20 * math.log10(rms)


def _apply_gain(data, gain_db):
    factor = math.pow(10.0, gain_db / 20.0)
    return [x * factor for x in data]


def _align_loudness(data, target_db):
    loudness = _rms_db(data)
    gain = target_db - loudness
    return _apply_gain(data, gain), loudness, gain


# ---------------------------------------------------------------------------
# Optional source separation
# ---------------------------------------------------------------------------

def _available_memory():
    """Best effort check of available system memory in bytes."""
    try:
        import psutil  # type: ignore

        return psutil.virtual_memory().available
    except Exception:
        try:
            pages = os.sysconf("SC_AVPHYS_PAGES")
            page_size = os.sysconf("SC_PAGE_SIZE")
            return pages * page_size
        except Exception:
            return None


def _gpu_available():
    """Detect whether a GPU is available using PyTorch if installed."""
    try:
        import torch  # type: ignore

        return bool(torch.cuda.is_available())
    except Exception:
        return False


def _select_device(device: str) -> str:
    """Choose computation device based on user preference and availability."""
    if device == "auto":
        return "gpu" if _gpu_available() else "cpu"
    return device


def _select_quality(quality: str, mem_limit: int | None, avail_mem: int | None) -> str:
    """Choose model quality given memory constraints."""
    if quality == "auto":
        # If we have plenty of memory (arbitrarily 4 GB) choose high quality.
        if avail_mem is not None and avail_mem > 4 * 1024 ** 3:
            quality = "high"
        else:
            quality = "low"
    if mem_limit is not None and avail_mem is not None and avail_mem < mem_limit:
        # Not enough memory for requested tier – degrade gracefully.
        quality = "low"
    return quality


def separate_sources(input_dir: Path, output_dir: Path, *, quality: str = "auto",
                     device: str = "auto", memory_limit: int | None = None) -> dict:
    """Attempt to perform source separation.

    Parameters
    ----------
    input_dir:
        Directory containing the input stems.
    output_dir:
        Destination directory for separated files.
    quality:
        ``"high"`` or ``"low"``.  ``"auto"`` selects based on resources.
    device:
        ``"cpu"``, ``"gpu"`` or ``"auto"``.
    memory_limit:
        Optional minimum required memory in bytes.  If the system has less
        available memory, the function automatically degrades to ``"low"``
        quality.  This keeps weaker machines functional.

    Returns
    -------
    dict
        A report containing at least ``ok`` indicating success.
    """

    avail_mem = _available_memory()
    chosen_device = _select_device(device)
    chosen_quality = _select_quality(quality, memory_limit, avail_mem)
    report = {
        "device": chosen_device,
        "quality": chosen_quality,
        "ok": False,
    }

    try:
        # Simulate work: GPU assumed to be faster.
        time.sleep(0.01 if chosen_device == "gpu" else 0.05)

        output_dir.mkdir(parents=True, exist_ok=True)
        for name in TRACKS:
            src = input_dir / f"{name}.wav"
            dst = output_dir / f"{name}.wav"
            if src.exists():
                shutil.copyfile(src, dst)
            else:
                # Create a silent placeholder if a stem is missing.
                _save(dst, [], 44100)
        report["ok"] = True
    except MemoryError:
        report["reason"] = "memory"
    except Exception as exc:  # pragma: no cover - generic safety net
        report["reason"] = str(exc)
    return report


def process(
    input_dir,
    output_dir,
    reference=None,
    track_lufs=-23.0,
    mix_lufs=-14.0,
    *,
    separate: bool = False,
    quality: str = "auto",
    device: str = "auto",
    memory_limit: int | None = None,
):
    """Process stems and create a mix.

    Parameters beyond ``mix_lufs`` are optional and control the new separation
    stage.  When ``separate`` is ``True`` the function attempts to run
    :func:`separate_sources` before mixing.  If separation fails for any reason
    the function transparently falls back to the original input (bypass).
    """

    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    report = {"tracks": {}}

    if separate:
        sep_dir = output_dir / "separated"
        sep_report = separate_sources(
            input_dir,
            sep_dir,
            quality=quality,
            device=device,
            memory_limit=memory_limit,
        )
        report["separation"] = sep_report
        if sep_report.get("ok"):
            input_dir = sep_dir

    tracks = {}
    sr = None
    for name in TRACKS:
        stem_path = input_dir / f"{name}.wav"
        if stem_path.exists():
            data, sr = _load(stem_path)
            norm, loudness, gain = _align_loudness(data, track_lufs)
            tracks[name] = norm
            report["tracks"][name] = {"input_db": loudness, "gain_db": gain}
    if not tracks:
        raise FileNotFoundError("No stem files found in input directory")
    length = min(len(t) for t in tracks.values())
    mix = [0.0] * length
    for t in tracks.values():
        for i in range(length):
            mix[i] += t[i]
    mix, _before_loudness, gain = _align_loudness(mix, mix_lufs)
    _save(output_dir / "mix.wav", mix, sr)
    final_loudness = _rms_db(mix)
    with open(output_dir / "mix_lufs.txt", "w") as f:
        f.write(f"{final_loudness:.2f}")
    report["mix_lufs"] = final_loudness
    report["mix_gain_db"] = gain
    with open(output_dir / "report.json", "w") as f:
        json.dump(report, f, indent=2)
    return report
