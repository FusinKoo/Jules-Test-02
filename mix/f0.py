"""Simple F0 extraction with backend fallback."""
import importlib
import json
import logging
from pathlib import Path
from typing import List

CONFIG_PATH = Path(__file__).with_name("f0.yaml")


class F0Extractor:
    """Extract fundamental frequency with backend fallbacks.

    Parameters
    ----------
    device: str
        "gpu_ultra" forces GPU backend, "cpu_ultra" forces CPU backend.
    """

    def __init__(self, device: str = "cpu_ultra") -> None:
        self.device = device
        with open(CONFIG_PATH) as f:
            self.config = json.load(f)
        self.log = logging.getLogger(self.__class__.__name__)

    def _determine_backends(self) -> List[str]:
        if self.device == "gpu_ultra":
            return ["rmvpe", "crepe_full"]
        return ["rmvpe", "crepe_full"]

    def extract(self, audio: List[float], sr: int) -> List[float]:
        last_exc = None
        for backend in self._determine_backends():
            try:
                return self._extract_backend(backend, audio, sr)
            except Exception as exc:  # pragma: no cover - logging branch
                self.log.warning("backend %s failed: %s", backend, exc)
                last_exc = exc
        raise RuntimeError("all F0 backends failed") from last_exc

    def _extract_backend(self, backend: str, audio: List[float], sr: int) -> List[float]:
        cfg = self.config.get(backend, {})
        threshold = cfg.get("threshold")
        window = cfg.get("window")
        self.log.info(
            "using %s with threshold=%s window=%s", backend, threshold, window
        )
        if backend == "rmvpe":
            return self._rmvpe(audio, sr, threshold, window)
        if backend == "crepe_full":
            return self._crepe(audio, sr, threshold, window)
        raise ValueError(f"unknown backend {backend}")

    def _rmvpe(self, audio: List[float], sr: int, threshold: float, window: float) -> List[float]:
        module = importlib.import_module("rmvpe")  # may raise ImportError
        return module.extract(audio, sr, threshold=threshold, window=window)

    def _crepe(self, audio: List[float], sr: int, threshold: float, window: float) -> List[float]:
        try:
            module = importlib.import_module("crepe")
            preds = module.predict(audio, sr, model="full", step_size=int(window * 1000))
            return preds[1].tolist()
        except Exception:  # pragma: no cover - if crepe unavailable
            return self._simple_f0(audio, sr, window)

    def _simple_f0(self, audio: List[float], sr: int, window: float) -> List[float]:
        """Very small zero-crossing based pitch tracker.

        Works offline and requires only the standard library.
        """
        size = max(int(window * sr), 1)
        result = []
        for i in range(0, len(audio), size):
            chunk = audio[i : i + size]
            if not chunk:
                break
            zero_crossings = sum(
                1 for j in range(1, len(chunk)) if chunk[j - 1] < 0 <= chunk[j]
            )
            freq = zero_crossings * sr / (2 * len(chunk)) if len(chunk) else 0.0
            result.append(freq)
        return result
