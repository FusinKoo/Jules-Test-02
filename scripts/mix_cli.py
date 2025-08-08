#!/usr/bin/env python
"""Command line interface for the mixing library."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import torch
except Exception:  # pragma: no cover
    torch = None

from mix import process

def main():
    parser = argparse.ArgumentParser(description="Mix stems into a single track")
    parser.add_argument("input", help="input directory containing stems")
    parser.add_argument("output", help="output directory")
    parser.add_argument("--reference", help="optional reference track")
    parser.add_argument(
        "--model",
        choices=["basic", "advanced"],
        default="basic",
        help="mixing model to use",
    )
    parser.add_argument(
        "--quality",
        choices=["low", "medium", "high"],
        default="medium",
        help="quality grade",
    )
    parser.add_argument(
        "--track-lufs",
        type=float,
        default=-23.0,
        help="target loudness for individual tracks",
    )
    parser.add_argument(
        "--mix-lufs",
        type=float,
        default=-14.0,
        help="target loudness for final mix",
    )
    args = parser.parse_args()
    device = "cuda" if (torch and torch.cuda.is_available()) else "cpu"
    print(f"Using device: {device}")
    print(f"Model: {args.model}, Quality: {args.quality}")
    report = process(
        Path(args.input),
        Path(args.output),
        reference=args.reference,
        track_lufs=args.track_lufs,
        mix_lufs=args.mix_lufs,
    )
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
