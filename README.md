
# Auto Mixing Toolkit

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/FusinKoo/Jules-Test-02/blob/main/notebooks/demo.ipynb)

This repository provides a minimal library, command line tools and a demo notebook for automatic music mixing.

## Structure

```
/mix/               # Reusable mixing library
/scripts/           # Command line interfaces
/tests/smoke/       # Smoke tests (stems generated at runtime)
/notebooks/         # Demonstration notebook
```

## Colab

Open the notebook via the badge above. The first cell installs system and Python dependencies (including GPU support if available). The second cell generates short sine‑wave stems and mixes them using `scripts/mix_cli.py`.

## Command line

Install system dependency and Python packages:

```
apt-get -y install ffmpeg
pip install -r requirements-colab-cpu.txt  # or requirements-colab-gpu.txt
```

Mix stems located in a folder:

```
python scripts/mix_cli.py /path/to/input /path/to/output
```

Input stems are expected as `vocals.wav`, `drums.wav`, `bass.wav` and `other.wav`. Outputs are written to the output directory:
- `mix.wav` – the mixed audio
- `mix_lufs.txt` – measured loudness
- `report.json` – gain applied to each track

### Unified pipeline interface

For more advanced processing the repository provides two pipeline scripts –
`scripts/pipeline.py` for local files and `scripts/pipeline_gdrive.py` for a
Google Drive environment. Both expose the same command line options so that the
notebook and batch scripts can invoke them in a consistent way:

```bash
python scripts/pipeline.py --input INPUT_DIR --output OUTPUT_DIR \
    --rvc_model MODEL.pth --f0_method rmvpe \
    --quality_profile medium --lufs_target -14 \
    --truepeak_margin -1 --dry_run
```

Arguments:

- `--input` – input file or directory.
- `--output` – output directory.
- `--rvc_model` – path to the RVC model.
- `--f0_method` – pitch extraction method.
- `--quality_profile` – quality/speed trade‑off.
- `--lufs_target` – target loudness in LUFS.
- `--truepeak_margin` – true peak margin in dB.
- `--dry_run` – run without producing output.

## Tests

Run the smoke test which generates 5‑second stems and mixes them:

```
PYTHONPATH=. pytest tests/smoke/test_mix.py
```

## Deterministic runs

Use the helper in `mix.deterministic` to reduce run‑to‑run variation across
CPU and GPU backends. The command line accepts a seed which enables
deterministic flags for NumPy, PyTorch and cuDNN:

```
python scripts/mix_cli.py input_dir output_dir --seed 0
```

This sets random seeds, fixes STFT parameters (1024 FFT, 256 hop, Hann window)
and requests deterministic kernels. Remaining differences are due to floating
point rounding in third‑party libraries.
