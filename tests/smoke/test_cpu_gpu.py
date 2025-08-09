import wave
from pathlib import Path

import pytest
import shutil
torch = pytest.importorskip("torch")  # type: ignore
pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")

from mix import _align_loudness, _save, _measure


def _render(device: str, path: Path):
    sr = 48000
    t = torch.arange(0, sr, device=device, dtype=torch.float32) / sr
    audio = torch.sin(2 * torch.pi * 440 * t).cpu().tolist()
    norm, _, _ = _align_loudness(audio, -14.0)
    _save(path, norm, sr)
    with wave.open(str(path), "rb") as wf:
        assert wf.getframerate() == 48000
        assert wf.getsampwidth() == 3
        length = wf.getnframes()
    lufs, tp_db = _measure(path)
    return lufs, tp_db, length


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

