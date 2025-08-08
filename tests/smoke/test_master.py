import math
from mix import master


def _tone(freq=440.0, amp=0.2, duration=1, sr=44100):
    return [amp * math.sin(2 * math.pi * freq * i / sr) for i in range(int(duration * sr))]


def test_master_loudness():
    base = _tone()
    sr = 44100
    # create 10 inputs with varying impulse peaks
    peaks = [0.2 * i for i in range(10)]  # 0.0 .. 1.8
    for i, peak in enumerate(peaks):
        data = base.copy()
        idx = min(i * 1000, len(data) - 1)
        data[idx] += peak
        processed, report = master(data)
        assert abs(report["output_lufs"] - (-14.0)) < 1.0
        assert report["output_tp"] <= -0.9  # allow small tolerance
