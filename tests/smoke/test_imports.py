import numpy as np
import numba
import librosa

def test_import_and_resample():
    y = np.zeros(22050)
    z = librosa.resample(y, orig_sr=22050, target_sr=48000, res_type="soxr_vhq")
    assert abs(z.shape[0] - 48000) <= 1
