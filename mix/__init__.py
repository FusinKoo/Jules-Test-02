"""Minimal audio mixing library using only the Python standard library."""
from pathlib import Path
import json
import wave
import array
import math

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


def process(input_dir, output_dir, reference=None, track_lufs=-23.0, mix_lufs=-14.0):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    tracks = {}
    report = {"tracks": {}}
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

from .f0 import F0Extractor  # noqa: E402

__all__ = ["TRACKS", "process", "F0Extractor"]
