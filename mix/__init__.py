"""Minimal audio mixing library with high quality resampling.

Audio is mixed in a fixed internal processing format of 48 kHz / float. If
input stems use a different sample rate they are resampled on load using
`soxr` with the "best" quality setting when available. When `soxr` is not
installed a simple linear interpolation resampler is used as a fallback.
The final mix is written as 48 kHz / 24-bit PCM and the processing report
includes a list of sample rate conversion points.
"""

from pathlib import Path
import json
import wave
import array
import math

TRACKS = ["vocals", "drums", "bass", "other"]
INTERNAL_SR = 48_000

try:  # optional dependency
    import soxr  # type: ignore
except Exception:  # pragma: no cover - handled gracefully
    soxr = None


def _resample(data, src_sr, dst_sr):
    if src_sr == dst_sr:
        return data
    if soxr is not None:
        return list(soxr.resample(data, src_sr, dst_sr, quality="best"))
    # fallback: linear interpolation
    ratio = dst_sr / src_sr
    n = int(round(len(data) * ratio))
    result = [0.0] * n
    for i in range(n):
        x = i / ratio
        i0 = int(math.floor(x))
        i1 = min(i0 + 1, len(data) - 1)
        frac = x - i0
        result[i] = data[i0] * (1 - frac) + data[i1] * frac
    return result


def _load(path):
    with wave.open(str(path), "rb") as wf:
        sr = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
        data = array.array("h", frames)
    data = [s / 32768.0 for s in data]
    orig_sr = sr
    if sr != INTERNAL_SR:
        data = _resample(data, sr, INTERNAL_SR)
    return data, orig_sr


def _float_to_24bit_bytes(data):
    max_int = 2 ** 23 - 1
    for x in data:
        v = max(-1.0, min(1.0, x))
        iv = int(v * max_int)
        yield int(iv).to_bytes(4, "little", signed=True)[:3]


def _save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = b"".join(_float_to_24bit_bytes(data))
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(3)
        wf.setframerate(INTERNAL_SR)
        wf.writeframes(frames)


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
    report = {"tracks": {}, "sample_rate_conversions": []}

    for name in TRACKS:
        stem_path = input_dir / f"{name}.wav"
        if stem_path.exists():
            data, orig_sr = _load(stem_path)
            if orig_sr != INTERNAL_SR:
                report["sample_rate_conversions"].append(
                    {"stage": f"input_{name}", "from": orig_sr, "to": INTERNAL_SR}
                )
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
    _save(output_dir / "mix.wav", mix)

    final_loudness = _rms_db(mix)
    with open(output_dir / "mix_lufs.txt", "w") as f:
        f.write(f"{final_loudness:.2f}")

    report["mix_lufs"] = final_loudness
    report["mix_gain_db"] = gain

    with open(output_dir / "report.json", "w") as f:
        json.dump(report, f, indent=2)

    return report

