"""Minimal audio mixing library using pyloudnorm for loudness and true-peak."""
from pathlib import Path
import json
import wave
import math
import array

try:  # pragma: no cover - dependency is validated in tests
    import pyloudnorm as pyln
except Exception as exc:  # pragma: no cover - optional dependency
    raise RuntimeError("pyloudnorm library is required for loudness measurement") from exc

from .config import get_config


def _load(path: Path, target_sr: int = 48000) -> tuple[list[float], int]:
    """Load a mono WAV file and resample to ``target_sr`` if needed."""
    with wave.open(str(path), "rb") as wf:
        sr = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
        data = array.array("h", frames)
    data = [s / 32768.0 for s in data]
    if sr != target_sr:
        try:
            import soxr  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("soxr library is required for resampling") from exc
        data = list(soxr.resample(data, sr, target_sr, quality="best"))
        sr = target_sr
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


def _measure_loudness_tp(data, sr):
    """Measure integrated loudness and true peak using pyloudnorm."""
    meter = pyln.Meter(sr)  # ITU-R BS.1770 compliant
    loudness = meter.integrated_loudness(data)
    true_peak = meter.true_peak(data)
    return loudness, true_peak


def _apply_gain(data, gain_db):
    factor = math.pow(10.0, gain_db / 20.0)
    return [x * factor for x in data]


def _align_loudness(data, target_db, sr):
    loudness, _ = _measure_loudness_tp(data, sr)
    gain = target_db - loudness
    return _apply_gain(data, gain), loudness, gain


def _limit_true_peak(data, sr, margin_db):
    """Apply a final true-peak limiter and re-measure."""
    loudness, true_peak = _measure_loudness_tp(data, sr)
    gain = 0.0
    if true_peak > margin_db:
        gain = margin_db - true_peak
        data = _apply_gain(data, gain)
        loudness, true_peak = _measure_loudness_tp(data, sr)
    return data, gain, loudness, true_peak


def process(
    input_dir,
    output_dir,
    reference=None,
    track_lufs=None,
    mix_lufs=None,
    truepeak_margin=None,
    profile=None,
    tracks=None,
):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    cfg = get_config(profile)
    tracks = tracks or cfg.get("tracks", [])
    track_lufs = track_lufs if track_lufs is not None else cfg.get("track_lufs", -23.0)
    mix_lufs = mix_lufs if mix_lufs is not None else cfg.get("mix_lufs", -14.0)
    truepeak_margin = (
        truepeak_margin if truepeak_margin is not None else cfg.get("truepeak_margin", -1.0)
    )
    report = {
        "tracks": {},
        "config": {
            "track_lufs": track_lufs,
            "mix_lufs": mix_lufs,
            "truepeak_margin": truepeak_margin,
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
            norm, loudness, gain = _align_loudness(data, track_lufs, sr)
            data_tracks[name] = norm
            report["tracks"][name] = {"input_db": loudness, "gain_db": gain}
    if not data_tracks:
        raise FileNotFoundError("No stem files found in input directory")
    length = min(len(t) for t in data_tracks.values())
    mix = [0.0] * length
    for t in data_tracks.values():
        for i in range(length):
            mix[i] += t[i]
    mix, _before_loudness, gain = _align_loudness(mix, mix_lufs, sr)
    mix, limit_gain, final_loudness, final_tp = _limit_true_peak(
        mix, sr, truepeak_margin
    )
    _save(output_dir / "mix.wav", mix, sr)
    with open(output_dir / "mix_lufs.txt", "w") as f:
        f.write(f"{final_loudness:.2f}")
    report["mix_lufs"] = final_loudness
    report["mix_true_peak"] = final_tp
    report["mix_gain_db"] = gain
    report["limit_gain_db"] = limit_gain
    with open(output_dir / "report.json", "w") as f:
        json.dump(report, f, indent=2)
    return report

from .f0 import F0Extractor  # noqa: E402

__all__ = ["TRACKS", "process", "F0Extractor"]
