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


def _true_peak_db(data, oversample=4):
    """Approximate true-peak level in dBFS with simple oversampling."""
    if not data:
        return -float("inf")
    peak = 0.0
    prev = data[0]
    for cur in data[1:]:
        for i in range(oversample):
            t = i / oversample
            val = prev + (cur - prev) * t
            if abs(val) > peak:
                peak = abs(val)
        prev = cur
    if peak == 0.0:
        return -float("inf")
    return 20 * math.log10(peak)


def _soft_limit(data, peak_db=-1.0):
    """Softly limit samples above the given peak (in dBFS)."""
    threshold = math.pow(10.0, peak_db / 20.0)
    limited = []
    for x in data:
        if abs(x) <= threshold:
            limited.append(x)
        else:
            limited.append(math.tanh(x / threshold) * threshold)
    return limited


def master(data, target_lufs=-14.0, target_tp=-1.0):
    """Master a mono track to the given loudness and true-peak targets.

    Returns the processed audio and a report of loudness/peak measurements.
    """
    processed, in_lufs, gain = _align_loudness(data, target_lufs)
    pre_lufs = _rms_db(processed)
    pre_tp = _true_peak_db(processed)
    limited = _soft_limit(processed, peak_db=target_tp)
    report = {
        "input_lufs": in_lufs,
        "input_tp": _true_peak_db(data),
        "gain_db": gain,
        "pre_limit_lufs": pre_lufs,
        "pre_limit_tp": pre_tp,
        "output_lufs": _rms_db(limited),
        "output_tp": _true_peak_db(limited),
    }
    return limited, report


def master_file(input_path, output_path, target_lufs=-14.0, target_tp=-1.0):
    """File based wrapper around :func:`master`."""
    data, sr = _load(input_path)
    processed, report = master(data, target_lufs=target_lufs, target_tp=target_tp)
    _save(output_path, processed, sr)
    with open(Path(output_path).with_suffix(".json"), "w") as f:
        json.dump(report, f, indent=2)
    return report


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
