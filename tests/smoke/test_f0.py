import math
from mix.f0 import F0Extractor


def _sine(freq=440, duration=0.1, sr=16000):
    return [math.sin(2 * math.pi * freq * i / sr) for i in range(int(duration * sr))]


def test_f0_fallback_and_consistency():
    audio = _sine()
    sr = 16000
    gpu = F0Extractor("gpu_ultra").extract(audio, sr)
    cpu = F0Extractor("cpu_ultra").extract(audio, sr)
    assert gpu and cpu
    # average absolute difference across shared length
    diff = sum(abs(a - b) for a, b in zip(gpu, cpu)) / min(len(gpu), len(cpu))
    assert diff < 1.0
