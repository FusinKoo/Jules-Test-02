from pathlib import Path
import math
import wave
import array
import pytest
from mix import process, _measure_loudness_tp


def _write_tone(path, freq, duration=5, sr=48000):
    """Generate a mono sine wave and write it as a WAV file."""
    t = [math.sin(2 * math.pi * freq * i / sr) for i in range(int(duration * sr))]
    ints = array.array("h", [int(max(-1.0, min(1.0, x)) * 32767) for x in t])
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(ints.tobytes())

def _measure_lufs_tp(path, head_gap=48000):
    with wave.open(str(path), "rb") as wf:
        assert wf.getsampwidth() == 3
        sr = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
    ints = [int.from_bytes(frames[i:i+3], byteorder="little", signed=True)
            for i in range(0, len(frames), 3)]
    data = [s / (2 ** 23) for s in ints]
    data = data[head_gap:] if head_gap < len(data) else []
    loudness, tp = _measure_loudness_tp(data, sr) if data else (-float("inf"), -float("inf"))
    return loudness, tp


def _make_stems(directory, sr=48000):
    freqs = {"vocals": 440, "drums": 220, "bass": 110, "other": 330}
    for name, freq in freqs.items():
        _write_tone(directory / f"{name}.wav", freq, sr=sr)

def test_mix(tmp_path):
    inp = tmp_path / "input"
    _make_stems(inp)
    out = tmp_path / "out"
    report = process(inp, out)
    mix_file = out / "mix.wav"
    assert mix_file.exists()
    with wave.open(str(mix_file), "rb") as wf:
        assert wf.getsampwidth() == 3
        assert wf.getframerate() == 48000
        head = wf.readframes(48000)
        assert head == b"\x00\x00\x00" * 48000
    loudness, tp = _measure_lufs_tp(mix_file)
    assert abs(loudness - (-14.0)) < 1.0
    assert tp <= -1.0 + 0.1
    assert "mix_lufs" in report
    assert "mix_true_peak" in report
    assert abs(loudness - report["mix_lufs"]) < 1e-5
    assert "tracks" in report


def test_resample_to_48k(tmp_path):
    soxr = pytest.importorskip("soxr")  # type: ignore
    inp = tmp_path / "input"
    _make_stems(inp, sr=44100)
    out = tmp_path / "out"
    process(inp, out)
    with wave.open(str(out / "mix.wav"), "rb") as wf:
        assert wf.getframerate() == 48000
