import array
import wave

import pytest

from mix import process
from mix.deterministic import enable_determinism, stft

from tests.smoke.test_mix import _make_stems

torch = pytest.importorskip("torch")


def _peak_db(tensor):
    peak = torch.max(torch.abs(tensor))
    if peak == 0:
        return -float("inf")
    return 20 * torch.log10(peak).item()


def test_cpu_gpu_alignment(tmp_path):
    enable_determinism(0)
    inp = tmp_path / "input"
    _make_stems(inp)
    out = tmp_path / "out"
    report = process(inp, out)
    mix_path = out / "mix.wav"
    with wave.open(str(mix_path), "rb") as wf:
        frames = wf.readframes(wf.getnframes())
    ints = array.array("h", frames)
    data = torch.tensor([s / 32768.0 for s in ints], dtype=torch.float32)

    cpu_lufs = 20 * torch.log10(torch.sqrt(torch.mean(data ** 2))).item()
    assert abs(cpu_lufs - report["mix_lufs"]) < 1e-6

    if not (torch and torch.cuda.is_available()):
        pytest.skip("CUDA not available")
    gpu_data = data.to("cuda")
    assert data.shape == gpu_data.shape

    spec_cpu = stft(data)
    spec_gpu = stft(gpu_data).cpu()
    max_diff = torch.max(torch.abs(spec_cpu - spec_gpu)).item()
    assert max_diff < 1e-6

    gpu_lufs = 20 * torch.log10(torch.sqrt(torch.mean(gpu_data ** 2))).item()
    assert abs(cpu_lufs - gpu_lufs) < 0.1

    peak_cpu = _peak_db(data)
    peak_gpu = _peak_db(gpu_data)
    assert abs(peak_cpu - peak_gpu) < 0.2
