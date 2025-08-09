# Auto Mixing Toolkit

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/FusinKoo/Jules-Test-02/blob/main/notebooks/demo.ipynb)
Mix four audio stems (`vocals.wav`, `drums.wav`, `bass.wav`, `other.wav`) into a single track.

## Environment Requirements

- Linux with Python 3.8+
- `ffmpeg` command line tool
- Python packages: `pip install -r requirements-colab-cpu.txt` or `requirements-colab-gpu.txt`

## One-click Start

Launch the Colab notebook via the badge above and run all cells:

1. Installs dependencies (ffmpeg, PyTorch, the library).
2. Generates short sine-wave stems and mixes them using `scripts/mix_cli.py`.

After execution `mix.wav`, `mix_lufs.txt` and `report.json` appear in the notebook's working directory.

## UI Usage

To mix your own stems inside the notebook:

1. Upload a folder containing `vocals.wav`, `drums.wav`, `bass.wav` and `other.wav`.
2. Run:

```python
!python scripts/mix_cli.py /content/your_songs/ /content/output/
```

3. Download the files from `/content/output/`.

## Batch Processing

For multiple songs use `scripts/batch_mix.py`:

```bash
python scripts/batch_mix.py /path/to/input_root /path/to/output_root
```

Each subfolder of `input_root` must contain the four stem files.

## Common Faults

- **`ffmpeg: command not found`** – install `ffmpeg`.
- **Missing stem file** – ensure all four stems exist with the expected names.
- **`Using device: cpu` when expecting GPU** – check CUDA availability in Colab or install GPU drivers locally.

## Quality Notes

This project demonstrates automatic level balancing. It is not a full mixing solution and may not match professional results.

## FAQ

**Q: What audio formats are supported?**
A: Only 48 kHz WAV files are tested.

**Q: How long can stems be?**
A: The library has been tested on stems up to a few minutes; longer tracks may require more memory.

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

Run the smoke tests that generate synthetic stems and check both CPU and GPU paths:

```bash
PYTHONPATH=. pytest tests/smoke -q
```

Exports are verified to be 48 kHz/24‑bit and CPU/GPU loudness and true peak
measurements must agree within 0.1 LUFS and 0.2 dB.

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
