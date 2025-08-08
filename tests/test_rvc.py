from array import array
import math

from mix.rvc import RVCInferenceConfig, peak_guard, time_align, run


def dummy_model(x: array) -> array:
    """Simple model introducing gain and delay."""
    delayed = array('f', [0.0] * 10)
    delayed.extend(v * 2.0 for v in x)
    return delayed


def _max_abs(a: array) -> float:
    return max((abs(x) for x in a), default=0.0)


def test_peak_guard_limits_amplitude():
    audio = array('f', [0.5, 2.0, -2.0])
    guarded = peak_guard(audio, peak_db=-1.0)
    limit = 10 ** (-1.0 / 20.0)
    assert _max_abs(guarded) <= limit + 1e-6


def test_time_align_recovers_shift():
    ref = array('f', [0.0] * 1000)
    ref[100] = 1.0
    tgt = array('f', [0.0] * 1000)
    tgt[110] = 1.0  # 10-sample delay
    aligned = time_align(ref, tgt, sr=1000, max_shift=0.05)
    assert aligned.index(1.0) == 100


def test_run_pipeline():
    audio = array('f', [math.sin(0.01 * i) for i in range(1000)])
    cfg = RVCInferenceConfig(sr=1000)
    out = run(dummy_model, audio, cfg)
    limit = 10 ** (cfg.peak_db / 20.0)
    assert isinstance(out, array)
    assert out.typecode == 'f'
    assert len(out) == len(audio)
    assert _max_abs(out) <= limit + 1e-6
