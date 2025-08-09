# Auto Mixing Toolkit

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/FusinKoo/Jules-Test-02/blob/main/notebooks/demo.ipynb)
Mix four audio stems (`vocals.wav`, `drums.wav`, `bass.wav`, `other.wav`) into a single track.
Processing runs at 48 kHz float32 with best-quality `soxr` resampling and
exports 48 kHz/24‑bit WAV files with TPDF dithering and 1 dB true‑peak margin.

## Environment Requirements

- Linux with Python 3.8+
- Audio utilities: `ffmpeg`, `sox`, `libsndfile1`
- Python packages: `pip install -r requirements-colab-cpu.txt` or `requirements-colab-gpu.txt`
  (both pin `numpy<2.1`, `numba` 0.57–0.59, `librosa==0.10.2.post1` and
  `soundfile>=0.12`)

## One-click Start

Launch the Colab notebook via the badge above.

1. Run the first **Environment Setup** cell. It attempts to install the
   audio utilities listed in `apt.txt` (including `ffmpeg`, `sox` and
   `libsndfile1`) via `apt-get` and then pulls `torch`, `torchvision` and
   `torchaudio` from a PyTorch index chosen at runtime. If `apt-get` is
   unavailable (e.g., due to network restrictions), the notebook skips this
   step and expects these tools to be installed separately. The cell detects
   the available CUDA version and prefers the matching `cu12x` index. Set
   `PYTORCH_INDEX_URL` to override this URL. If installation from the
   chosen index fails, the cell automatically falls back to the CPU wheels.
   It prints the selected index, package versions, `torch.cuda.is_available()`,
   `ffmpeg -version` and the resampling backend (expects `soxr`).
2. Execute the remaining cells to generate short sine‑wave stems and mix them
   using `scripts/mix_cli.py`.

After execution `mix.wav`, `mix_lufs.txt` and `report.json` appear in the notebook's working directory. The report contains the
final LUFS and true‑peak values measured with `ffmpeg`.

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

The script relies on the `BatchExecutor` helper located in `batch_executor.py`.

## Common Faults

- **`ffmpeg: command not found`** – install `ffmpeg`.
- **Missing stem file** – ensure all four stems exist with the expected names.
- **`Using device: cpu` when expecting GPU** – check CUDA availability in Colab or install GPU drivers locally.

## Quality Notes

This project demonstrates automatic level balancing. It is not a full mixing solution and may not match professional results.

## FAQ

**Q: What audio formats are supported?**
A: The toolkit processes audio internally at 48 kHz float32 and exports
48 kHz/24‑bit WAV files with TPDF dithering and 1 dB true‑peak margin. WAV
inputs at any sample rate are automatically resampled.

**Q: How long can stems be?**
A: The library has been tested on stems up to a few minutes; longer tracks may require more memory.

### Unified pipeline interface

For more advanced processing the repository provides two pipeline scripts –
`scripts/pipeline.py` for local files and `scripts/pipeline_gdrive.py` for a
Google Drive environment. Both expose the same command line options so that the
notebook and batch scripts can invoke them in a consistent way:

```bash
python scripts/pipeline.py --input INPUT_DIR --output OUTPUT_DIR \
    [--rvc_model MODEL.pth] --f0_method rmvpe \
    --quality_profile medium --lufs_target -14 \
    --truepeak_margin -1 --seed 0 --dry_run
```

Arguments:

- `--input` – input file or directory.
- `--output` – output directory.
- `--rvc_model` – override path to the RVC model (defaults to auto discovery).
- `--f0_method` – pitch extraction method.
- `--quality_profile` – quality/speed trade‑off.
- `--lufs_target` – target loudness in LUFS.
- `--truepeak_margin` – true peak margin in dB.
- `--seed` – set random seed and enable deterministic algorithms.
- `--dry_run` – run without producing output.

### Full-song processing in Colab

For a single mixed song the `scripts/colab_pipeline.py` helper performs an
end‑to‑end workflow: Demucs source separation, optional RVC voice conversion of
the vocal stem and final mixing via the library's processing chain.

```bash
python scripts/colab_pipeline.py --input song.wav --output OUTPUT_DIR \
    --rvc_model /content/drive/MyDrive/models/RVC/G_8200.pth
```

The script imports heavy dependencies lazily so unit tests remain lightweight.
Install `demucs` and an RVC inference library in the Colab environment before
running it.

## RVC model selection

By default the toolkit expects an RVC model at
`/content/drive/MyDrive/models/RVC/G_8200.pth`. All `.pth` files inside
`/content/drive/MyDrive/models/RVC/` are scanned on startup and presented as
candidates.

Model priority is:

1. `--rvc_model` command line argument
2. `RVC_MODEL` environment variable
3. Notebook drop‑down selection when multiple models are available

If none of these resolve to an existing file the default path is used. When no
model can be found an explicit error is raised with instructions to upload one
to the directory above.

## Tests

Run the smoke tests that generate synthetic stems and verify audio quality,
including 48 kHz/24‑bit output, LUFS/true‑peak targets and CPU/GPU parity:

```bash
PYTHONPATH=. pytest tests/smoke
```

## Deterministic runs

Use the helper in `mix.deterministic` to reduce run‑to‑run variation across
CPU and GPU backends. The command line accepts a seed which enables
deterministic flags for NumPy, PyTorch and cuDNN:

```
python scripts/mix_cli.py input_dir output_dir --seed 0
python scripts/pipeline.py --input INPUT_DIR --output OUTPUT_DIR --seed 0
```

This sets random seeds, fixes STFT parameters (1024 FFT, 256 hop, Hann window)
and requests deterministic kernels. Minor CPU/GPU differences stem from
floating‑point rounding in third‑party libraries. Empirically the maximum
deviation is about `1e-6` for STFT magnitudes, `0.1` LUFS for loudness and
`0.2` dB for peaks.
