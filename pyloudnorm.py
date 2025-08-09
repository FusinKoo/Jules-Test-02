"""Very small subset of the ``pyloudnorm`` API used for offline tests.

This module provides only the :class:`Meter` class with ``integrated_loudness``
and ``true_peak`` methods. It is **not** a complete ITU-R BS.1770
implementation but is sufficient for unit tests without external
dependencies.
"""
import math
from typing import Sequence


class Meter:
    """Minimal loudness meter operating on Python lists."""

    def __init__(self, rate: int, oversample: int = 4):
        self.rate = rate
        self.oversample = oversample

    def integrated_loudness(self, data: Sequence[float]) -> float:
        if not data:
            return float("-inf")
        rms = math.sqrt(sum(x * x for x in data) / len(data))
        if rms <= 0:
            return float("-inf")
        return 20 * math.log10(rms)

    def true_peak(self, data: Sequence[float]) -> float:
        if not data:
            return float("-inf")
        max_val = max(abs(x) for x in data)
        for i in range(len(data) - 1):
            start = data[i]
            end = data[i + 1]
            diff = end - start
            for k in range(1, self.oversample):
                interp = start + diff * (k / self.oversample)
                val = abs(interp)
                if val > max_val:
                    max_val = val
        if max_val <= 0:
            return float("-inf")
        return 20 * math.log10(max_val)


__all__ = ["Meter"]
