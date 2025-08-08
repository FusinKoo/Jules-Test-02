from pathlib import Path
import math
import wave
import array
from mix import process, TRACKS, _load, _align_loudness, _save
import pytest


def _write_tone(path, freq, duration=5, sr=44100):
    t = [math.sin(2 * math.pi * freq * i / sr) for i in range(int(duration * sr))]
    ints = array.array("h", [int(max(-1.0, min(1.0, x)) * 32767) for x in t])
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(ints.tobytes())


def _make_stems(directory):
    freqs = {"vocals": 440, "drums": 220, "bass": 110, "other": 330}
    for name, freq in freqs.items():
        _write_tone(directory / f"{name}.wav", freq)


def test_resume(tmp_path):
    inp = tmp_path / "input"
    _make_stems(inp)
    out = tmp_path / "out"
    # simulate failure after normalization
    for name in TRACKS:
        data, sr = _load(inp / f"{name}.wav")
        norm, _loud, _gain = _align_loudness(data, -23.0)
        _save(out / f"{name}_norm.wav", norm, sr)
    report = process(inp, out)
    assert all(t["cached"] for t in report["tracks"].values())
    mix_file = out / "mix.wav"
    assert mix_file.exists()
    mtime = mix_file.stat().st_mtime
    # simulate failure after mixing
    (out / "mix_lufs.txt").unlink()
    (out / "report.json").unlink()
    report2 = process(inp, out)
    assert mix_file.stat().st_mtime == mtime
    assert (out / "mix_lufs.txt").exists()
    assert (out / "report.json").exists()
    assert report2["mix_lufs"] == pytest.approx(report["mix_lufs"], abs=1e-3)
