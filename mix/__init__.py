"""Minimal audio mixing library using only the Python standard library.

This module now includes basic I/O management with automatic stem
discovery, intermediate caching and simple preflight checks so that a
failed run can be resumed without repeating work.  The implementation is
kept intentionally lightweight to remain within the standard library.
"""

from pathlib import Path
import json
import wave
import array
import math
import shutil
from typing import Iterable

from .config import get_config


def _load(path: Path):
    """Load a WAV file as floating point samples."""
    with wave.open(str(path), "rb") as wf:
        sr = wf.getframerate()
        sw = wf.getsampwidth()
        frames = wf.readframes(wf.getnframes())
    if sw == 2:
        data = array.array("h", frames)
        data = [s / 32768.0 for s in data]
    elif sw == 3:
        data = [
            int.from_bytes(frames[i : i + 3], byteorder="little", signed=True)
            / (2 ** 23)
            for i in range(0, len(frames), 3)
        ]
    else:
        raise ValueError("Unsupported sample width: %s" % sw)
    return data, sr


def _save(path, data, sr):
    import random
    import struct
    path.parent.mkdir(parents=True, exist_ok=True)
    target_sr = 48000
    if sr != target_sr:
        raise ValueError("Sample rate must be 48kHz")
    # convert to float32 for uniform quantisation
    data = [struct.unpack("f", struct.pack("f", x))[0] for x in data]
    peak_limit = math.pow(10.0, -1.0 / 20.0)
    peak = max((abs(x) for x in data), default=0.0)
    if peak > peak_limit:
        scale = peak_limit / peak
        data = [x * scale for x in data]
    head_gap = target_sr
    lsb = 1.0 / (2 ** 23)
    max_int = 2 ** 23 - 1
    frames = bytearray(b"\x00\x00\x00" * head_gap)
    for x in data:
        y = x + (random.random() - random.random()) * lsb
        y = max(-1.0, min(1.0 - lsb, y))
        n = int(round(y * max_int))
        frames.extend(n.to_bytes(3, "little", signed=True))
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(3)
        wf.setframerate(target_sr)
        wf.writeframes(frames)
    with wave.open(str(path), "rb") as wf:
        if wf.getsampwidth() != 3 or wf.getframerate() != target_sr:
            raise ValueError("Export verification failed")


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


def _preflight_check(output_dir: Path, model_paths: Iterable[Path] | None) -> None:
    """Ensure disk, model and GPU resources are available before running."""
    usage = shutil.disk_usage(output_dir if output_dir.exists() else output_dir.parent)
    if usage.free < 50 * 1024 * 1024:  # 50 MB
        raise RuntimeError("Insufficient disk space")
    if model_paths:
        for p in model_paths:
            if not Path(p).exists():
                raise FileNotFoundError(f"Model not found: {p}")
    try:  # GPU check is best-effort and skipped if torch is missing
        import torch

        if torch.cuda.is_available():
            free, _ = torch.cuda.mem_get_info()
            if free < 50 * 1024 * 1024:
                raise RuntimeError("Insufficient GPU memory")
    except Exception:
        pass


def process(
    input_dir,
    output_dir,
    reference=None,
    track_lufs=None,
    mix_lufs=None,
    profile=None,
    tracks=None,
    model_paths: Iterable[Path] | None = None,
):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    _preflight_check(output_dir, model_paths)
    cfg = get_config(profile)
    if tracks is None:
        detected = sorted(p.stem for p in input_dir.glob("*.wav"))
        tracks = detected or cfg.get("tracks", [])
    track_lufs = track_lufs if track_lufs is not None else cfg.get("track_lufs", -23.0)
    mix_lufs = mix_lufs if mix_lufs is not None else cfg.get("mix_lufs", -14.0)
    report = {
        "tracks": {},
        "config": {
            "track_lufs": track_lufs,
            "mix_lufs": mix_lufs,
            "tracks": tracks,
            "quality_profile": cfg.get("quality_profile"),
        },
    }
    cache_dir = output_dir / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    data_tracks = {}
    sr = None
    for name in tracks:
        cache_file = cache_dir / f"{name}.json"
        if cache_file.exists():
            with open(cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
            data_tracks[name] = cached["data"]
            sr = cached["sr"]
            track_rep = cached.get("report", {})
            track_rep["cached"] = True
            report["tracks"][name] = track_rep
            continue
        stem_path = input_dir / f"{name}.wav"
        if stem_path.exists():
            data, sr = _load(stem_path)
            norm, loudness, gain = _align_loudness(data, track_lufs)
            data_tracks[name] = norm
            track_rep = {"input_db": loudness, "gain_db": gain, "cached": False}
            report["tracks"][name] = track_rep
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump({"sr": sr, "data": norm, "report": track_rep}, f)
    if not data_tracks:
        raise FileNotFoundError("No stem files found in input directory")
    mix_file = output_dir / "mix.wav"
    report_file = output_dir / "report.json"
    lufs_file = output_dir / "mix_lufs.txt"
    if mix_file.exists() and report_file.exists() and lufs_file.exists():
        with open(report_file, "r", encoding="utf-8") as f:
            return json.load(f)
    length = min(len(t) for t in data_tracks.values())
    mix = [0.0] * length
    for t in data_tracks.values():
        for i in range(length):
            mix[i] += t[i]
    mix, _before_loudness, gain = _align_loudness(mix, mix_lufs)
    _save(mix_file, mix, sr)
    final_loudness = _rms_db(mix)
    with open(lufs_file, "w", encoding="utf-8") as f:
        f.write(f"{final_loudness:.2f}")
    report["mix_lufs"] = final_loudness
    report["mix_gain_db"] = gain
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return report

from .f0 import F0Extractor  # noqa: E402

__all__ = ["TRACKS", "process", "F0Extractor"]
