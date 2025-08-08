"""Utilities for deterministic and reproducible execution."""
import os
import random

try:
    import numpy as np
except Exception:  # pragma: no cover - numpy optional
    np = None

try:
    import torch
except Exception:  # pragma: no cover - torch optional
    torch = None

# Default STFT parameters to keep CPU/GPU behaviour aligned.
DEFAULT_FFT_SIZE = 1024
DEFAULT_HOP_LENGTH = 256
DEFAULT_WINDOW = "hann"


def enable_determinism(seed: int = 0) -> None:
    """Configure global libraries for deterministic behaviour.

    This function seeds Python, NumPy and PyTorch random number generators and
    toggles flags so that CUDA/cuDNN/BLAS produce repeatable results. It also
    sets environment variables known to impact determinism.
    """
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    if np is not None:
        np.random.seed(seed)
    if torch is not None:
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        torch.use_deterministic_algorithms(True)
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
        torch.backends.cuda.matmul.allow_tf32 = False


def stft(signal, n_fft: int = DEFAULT_FFT_SIZE, hop_length: int = DEFAULT_HOP_LENGTH):
    """Run a deterministic STFT using PyTorch.

    Parameters mirror :func:`torch.stft` but use a fixed Hann window and do not
    centre the signal, ensuring CPU/GPU parity.
    """
    if torch is None:
        raise RuntimeError("PyTorch is required for STFT")
    window = torch.hann_window(n_fft, device=signal.device)
    return torch.stft(signal, n_fft=n_fft, hop_length=hop_length, window=window,
                      center=False, return_complex=True)
