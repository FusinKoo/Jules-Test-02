import math
import wave
from pathlib import Path

import pytest
torch = pytest.importorskip("torch")  # type: ignore

from mix import _align_loudness, _save


def _render(device: str, path: Path):
    sr = 48000
    t = torch.arange(0, sr, device=device, dtype=torch.float32) / sr
    audio = torch.sin(2 * math.pi * 440 * t).cpu().tolist()
    norm, _, _ = _align_loudness(audio, -14.0)
    _save(path, norm, sr)
    with wave.open(str(path), "rb") as wf:
        assert wf.getframerate() == 48000
        assert wf.getsampwidth() == 3
        frames = wf.readframes(wf.getnframes())
    ints = [int.from_bytes(frames[i:i+3], byteorder="little", signed=True)
            for i in range(0, len(frames), 3)]
    floats = [s / (2 ** 23) for s in ints]
    rms = math.sqrt(sum(x * x for x in floats) / len(floats)) if floats else 0.0
    lufs = 20 * math.log10(rms) if rms > 0 else -float("inf")
    upsampled = []
    for i in range(len(floats) - 1):
        a = floats[i]
        b = floats[i + 1]
        upsampled.extend(a + (b - a) * k / 4 for k in range(4))
    upsampled.append(floats[-1]) if floats else None
    peak = max(abs(x) for x in upsampled) if upsampled else 0.0
    tp_db = 20 * math.log10(peak) if peak > 0 else -float("inf")
    return lufs, tp_db, len(floats)


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
def test_cpu_gpu_parity(tmp_path):
    cpu_path = tmp_path / "mix_cpu.wav"
    gpu_path = tmp_path / "mix_gpu.wav"
    lufs_cpu, tp_cpu, len_cpu = _render("cpu", cpu_path)
    lufs_gpu, tp_gpu, len_gpu = _render("cuda", gpu_path)
    assert abs(lufs_cpu - (-14.0)) < 0.5
    assert abs(tp_cpu - (-11.0)) < 0.2
    assert abs(lufs_gpu - (-14.0)) < 0.5
    assert abs(tp_gpu - (-11.0)) < 0.2
    assert abs(lufs_cpu - lufs_gpu) < 0.1
    assert abs(tp_cpu - tp_gpu) < 0.2
    assert len_cpu == len_gpu

