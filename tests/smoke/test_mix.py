from pathlib import Path
import math
import wave
import array

try:  # optional dependency
    import soundfile as sf  # type: ignore
except Exception:  # pragma: no cover - handled gracefully
    sf = None

from mix import process, INTERNAL_SR


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
    if sf is not None:
        data, _sr = sf.read(str(path), dtype="float32")
        rms = math.sqrt(sum(x * x for x in data) / len(data))
    else:
        with wave.open(str(path), "rb") as wf:
            frames = wf.readframes(wf.getnframes())
        data = []
        for i in range(0, len(frames), 3):
            chunk = frames[i : i + 3]
            if chunk[2] & 0x80:
                chunk += b"\xff"
            else:
                chunk += b"\x00"
            sample = int.from_bytes(chunk, "little", signed=True)
            data.append(sample / 8388608.0)
        rms = math.sqrt(sum(x * x for x in data) / len(data))
    return 20 * math.log10(rms)


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
    if sf is not None:
        info = sf.info(mix_file)
        assert info.samplerate == INTERNAL_SR
        assert info.subtype == "PCM_24"
    else:
        with wave.open(str(mix_file), "rb") as wf:
            assert wf.getframerate() == INTERNAL_SR
            assert wf.getsampwidth() == 3
    loudness = _rms_db(mix_file)
    assert abs(loudness - (-14.0)) < 1.0
    assert "mix_lufs" in report
    assert "tracks" in report
