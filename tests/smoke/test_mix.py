from pathlib import Path
import sys
import math
import wave
import array

# Ensure the package under test is importable when the tests are executed from
# arbitrary working directories.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mix import process


def _write_tone(path, freq, duration=5, sr=44100):
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

def _rms_db(path):
    with wave.open(str(path), "rb") as wf:
        frames = wf.readframes(wf.getnframes())
    data = array.array("h", frames)
    floats = [s/32768.0 for s in data]
    rms = math.sqrt(sum(x*x for x in floats)/len(floats))
    return 20*math.log10(rms)


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
    loudness = _rms_db(mix_file)
    assert abs(loudness - (-14.0)) < 1.0
    assert "mix_lufs" in report
    assert "tracks" in report


def test_mix_with_separation(tmp_path):
    """Separation switch should still produce a valid mix."""
    inp = tmp_path / "input"
    _make_stems(inp)
    out = tmp_path / "out"
    report = process(inp, out, separate=True)
    mix_file = out / "mix.wav"
    assert mix_file.exists()
    assert report.get("separation", {}).get("ok") is True
