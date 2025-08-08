# Auto Mixing Toolkit

This repository provides a minimal library, command line tools and a demo notebook
for automatic music mixing.

## Structure

```
/env/               # Conda environments for CPU and GPU
/mix/               # Reusable mixing library
/scripts/           # Command line interfaces
/tests/smoke/       # Smoke tests (stems generated at runtime)
/notebooks/         # Demonstration notebook
```

## Environment

Install system dependencies:

```
apt-get install $(cat apt.txt)
```

Create a conda environment:

```
conda env create -f env/environment.cpu.yml
```

For GPUs use `env/environment.gpu.yml`.

## Usage

Mix stems located in a folder:

```
python scripts/mix_cli.py /path/to/input /path/to/output
```

Input stems are expected as `vocals.wav`, `drums.wav`, `bass.wav` and `other.wav`.
Outputs are written to the output directory:
- `mix.wav` – the mixed audio
- `mix_lufs.txt` – measured loudness
- `report.json` – gain applied to each track

## Tests

Run the smoke test which generates 5‑second stems and mixes them:

```
pytest tests/smoke/test_mix.py
```
