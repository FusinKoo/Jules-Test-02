import wave
from pathlib import Path

import pytest

from mix import health


def _create_wav(path: Path, sr: int) -> None:
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(b"\x00\x00" * sr)


def test_sample_rate_error(tmp_path):
    _create_wav(tmp_path / "a.wav", 22050)
    errors = health.run_preflight_checks(
        input_dir=tmp_path, min_gpu_mem_mb=0, min_disk_mb=0
    )
    assert any("22050" in e for e in errors)


def test_model_missing():
    errors = health.run_preflight_checks(
        model_path="missing.pth", min_gpu_mem_mb=0, min_disk_mb=0
    )
    assert any("missing.pth" in e for e in errors)


def test_ffmpeg_missing(monkeypatch):
    monkeypatch.setattr(health.shutil, "which", lambda name: None)
    errors = health.run_preflight_checks(min_gpu_mem_mb=0, min_disk_mb=0)
    assert any("ffmpeg" in e for e in errors)


def test_disk_space(monkeypatch):
    class FakeUsage:
        total = 0
        used = 0
        free = 0

    monkeypatch.setattr(health.shutil, "disk_usage", lambda path: FakeUsage)
    errors = health.run_preflight_checks(min_gpu_mem_mb=0, min_disk_mb=1)
    assert any("disk space" in e for e in errors)


def test_gpu_memory(monkeypatch):
    class FakeCuda:
        @staticmethod
        def is_available():
            return True

        @staticmethod
        def mem_get_info():
            return (0, 1 << 30)  # 0 bytes free, 1GB total

    class FakeTorch:
        cuda = FakeCuda()

    monkeypatch.setattr(health, "torch", FakeTorch())
    errors = health.run_preflight_checks(min_gpu_mem_mb=1, min_disk_mb=0)
    assert any("GPU" in e for e in errors)
