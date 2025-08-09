#!/usr/bin/env python
"""Colab-friendly end-to-end processing pipeline.

This script accepts either a directory of stems or a single mixed audio file.
When given a single file it uses `demucs` to split the audio into stems, runs
RVC voice conversion on the vocal stem and finally mixes the result using the
`mix.process` function.  The goal is to provide a simple entry point for Google
Colab demos where users upload a song and obtain a processed mix.

Heavy optional dependencies such as `demucs` and an RVC inference library are
imported lazily so that regular unit tests remain lightweight.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import tempfile
import sys

import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mix import process
from mix.model_manager import get_model_path
from mix.rvc import run as rvc_run, RVCInferenceConfig


def _separate(input_file: Path, work_dir: Path) -> Path:
    """Run Demucs source separation and return directory with stems.

    Demucs writes stems to ``work_dir/input_file.stem``.  Only the ``vocals``
    and ``other`` stem are required for this minimal pipeline, but Demucs also
    produces ``drums`` and ``bass`` which are mixed as well.
    """
    try:  # pragma: no cover - optional dependency
        from demucs.separate import main as demucs_main
    except Exception as exc:  # pragma: no cover - Demucs missing
        raise RuntimeError(
            "Demucs is required for automatic stem separation. Install it via\n"
            "pip install demucs"
        ) from exc
    demucs_main(["--two-stems=vocals", "-o", str(work_dir), str(input_file)])
    return work_dir / input_file.stem


def _convert_vocals(vocal_path: Path, model_path: str, f0_method: str) -> None:
    """Replace the vocal track with an RVC-converted version."""
    audio, sr = sf.read(vocal_path)
    # TODO: replace the identity model with a real RVC inference call.
    def identity_model(x):
        return x

    converted = rvc_run(identity_model, audio.tolist(), RVCInferenceConfig(sr=sr))
    sf.write(vocal_path, converted, sr)


def main() -> None:
    parser = argparse.ArgumentParser(description="Full song processing pipeline")
    parser.add_argument("--input", required=True, help="input file or stem directory")
    parser.add_argument("--output", required=True, help="output directory")
    parser.add_argument("--rvc_model", help="path to the RVC model (.pth)")
    parser.add_argument("--f0_method", default="rmvpe", help="pitch extraction method")
    args = parser.parse_args()

    model_path = get_model_path(args.rvc_model)
    inp = Path(args.input)

    if inp.is_file():
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            stems_dir = _separate(inp, tmp)
            vocal = stems_dir / "vocals.wav"
            if vocal.exists():
                _convert_vocals(vocal, model_path, args.f0_method)
            report = process(stems_dir, Path(args.output))
    else:
        stems_dir = inp
        vocal = stems_dir / "vocals.wav"
        if vocal.exists():
            _convert_vocals(vocal, model_path, args.f0_method)
        report = process(stems_dir, Path(args.output))

    print(report)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
