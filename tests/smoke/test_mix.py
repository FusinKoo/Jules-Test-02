from pathlib import Path
import math
import wave
import array
import json
from mix import process, _measure


def _write_tone(path, freq, duration=5, sr=48000):
    """Generate a mono sine wave and write it as a WAV file."""
    t = [
        math.sin(2 * math.pi * freq * i / sr)
        for i in range(int(duration * sr))
    ]
    ints = array.array(
        "h", [int(max(-1.0, min(1.0, x)) * 32767) for x in t]
    )
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
    lufs, tp = _measure(mix_file, skip_seconds=1)
    assert abs(lufs - (-14.0)) < 1.0
    assert "mix_lufs" in report
    assert "mix_true_peak" in report
    assert "tracks" in report
    proc_path = out / "processing.json"
    assert proc_path.exists()
    with open(out / "report.json") as f:
        rep_file = json.load(f)
    with open(proc_path) as f:
        proc_file = json.load(f)
    assert rep_file == proc_file
