"""Minimal audio mixing library using only the Python standard library."""
from pathlib import Path
import json
import wave
import array
import math
import subprocess
import tempfile
import os

from .config import get_config


def _load(path):
    with wave.open(str(path), "rb") as wf:
        sr = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
        data = array.array("h", frames)
    # convert to float in [-1, 1]
    data = [s / 32768.0 for s in data]
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


def _apply_gain(data, gain_db):
    factor = math.pow(10.0, gain_db / 20.0)
    return [x * factor for x in data]


def _measure(path, skip_seconds=0.0):
    """Measure integrated loudness (LUFS) and true peak (dBTP) using ffmpeg."""
    filters = []
    if skip_seconds:
        filters.append(f"atrim=start={skip_seconds}")
    filters.append("loudnorm=print_format=json")
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-i",
        str(path),
        "-af",
        ",".join(filters),
        "-f",
        "null",
        "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    stderr = proc.stderr
    json_start = stderr.rfind("{")
    info = json.loads(stderr[json_start:])
    return float(info["input_i"]), float(info["input_tp"])


def _measure_data(data, sr):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        with wave.open(str(tmp_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            ints = array.array(
                "h", [int(max(-1.0, min(1.0, x)) * 32767) for x in data]
            )
            wf.writeframes(ints.tobytes())
        return _measure(tmp_path)
    finally:
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass


def process(
    input_dir,
    output_dir,
    reference=None,
    track_lufs=None,
    mix_lufs=None,
    profile=None,
    tracks=None,
):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    cfg = get_config(profile)
    tracks = tracks or cfg.get("tracks", [])
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
    data_tracks = {}
    sr = None
    for name in tracks:
        stem_path = input_dir / f"{name}.wav"
        if stem_path.exists():
            data, sr = _load(stem_path)
            lufs, tp = _measure(stem_path)
            gain = track_lufs - lufs
            norm = _apply_gain(data, gain)
            data_tracks[name] = norm
            report["tracks"][name] = {
                "input_lufs": lufs,
                "input_tp": tp,
                "gain_db": gain,
            }
    if not data_tracks:
        raise FileNotFoundError("No stem files found in input directory")
    length = min(len(t) for t in data_tracks.values())
    mix = [0.0] * length
    for t in data_tracks.values():
        for i in range(length):
            mix[i] += t[i]
    raw_lufs, _ = _measure_data(mix, sr)
    gain = mix_lufs - raw_lufs
    mix = _apply_gain(mix, gain)
    _save(output_dir / "mix.wav", mix, sr)
    final_lufs, final_tp = _measure(output_dir / "mix.wav", skip_seconds=1)
    with open(output_dir / "mix_lufs.txt", "w") as f:
        f.write(f"{final_lufs:.2f}")
    report["mix_lufs"] = final_lufs
    report["mix_true_peak"] = final_tp
    report["mix_gain_db"] = gain
    with open(output_dir / "report.json", "w") as f:
        json.dump(report, f, indent=2)
    with open(output_dir / "processing.json", "w") as f:
        json.dump(report, f, indent=2)
    return report

from .f0 import F0Extractor  # noqa: E402

__all__ = ["TRACKS", "process", "F0Extractor"]
