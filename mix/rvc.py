"""RVC inference helper utilities.

This module provides a small template for running RVC models
with float32 audio, peak limiting and simple time-domain
alignment.  The goal is to avoid clipping artefacts and maintain
phase coherence when comparing the model output with the input.
"""
from __future__ import annotations

from array import array
from dataclasses import dataclass
from typing import Callable, Sequence


@dataclass
class RVCInferenceConfig:
    """Configuration parameters for RVC inference."""

    dtype: str = "f"  # float32
    peak_db: float = -1.0
    guard_db: float = 0.3
    align_max: float = 0.02
    sr: int = 48000


def as_array(audio: Sequence[float]) -> array:
    """Return the data as a float32 array."""
    return array("f", audio)


def peak_guard(audio: Sequence[float], peak_db: float) -> array:
    """Limit audio to the requested peak level."""
    data = as_array(audio)
    limit = 10 ** (peak_db / 20.0)
    peak = max((abs(x) for x in data), default=0.0)
    if peak > limit and peak > 0.0:
        factor = limit / peak
        data = array("f", (x * factor for x in data))
    return data


def time_align(reference: Sequence[float], target: Sequence[float], sr: int, max_shift: float) -> array:
    """Align ``target`` to ``reference`` using brute-force correlation."""
    ref = as_array(reference)
    tgt = as_array(target)
    max_samples = int(max_shift * sr)
    best_shift = 0
    best_corr = float("-inf")
    for shift in range(-max_samples, max_samples + 1):
        corr = 0.0
        for i, r in enumerate(ref):
            j = i + shift
            if 0 <= j < len(tgt):
                corr += r * tgt[j]
        if corr > best_corr:
            best_corr = corr
            best_shift = shift
    if best_shift > 0:
        tgt = tgt[best_shift:]
    elif best_shift < 0:
        tgt = array("f", [0.0] * (-best_shift)) + tgt
    if len(tgt) < len(ref):
        tgt.extend([0.0] * (len(ref) - len(tgt)))
    else:
        del tgt[len(ref):]
    return tgt


def run(
    model: Callable[[array], Sequence[float]],
    audio: Sequence[float],
    cfg: RVCInferenceConfig | None = None,
) -> array:
    """Run an RVC model with pre/post processing."""
    if cfg is None:
        cfg = RVCInferenceConfig()
    x = peak_guard(audio, cfg.peak_db - cfg.guard_db)
    y_raw = model(as_array(x))
    y = as_array(y_raw)
    y = time_align(x, y, cfg.sr, cfg.align_max)
    y = peak_guard(y, cfg.peak_db)
    return y
