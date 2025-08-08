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
A: Only 44.1 kHz WAV files are tested.

**Q: How long can stems be?**
A: The library has been tested on stems up to a few minutes; longer tracks may require more memory.

## Tests

Run the smoke test that generates synthetic stems:

```bash
PYTHONPATH=. pytest tests/smoke/test_mix.py
```
