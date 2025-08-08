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
try:
    from mix.deterministic import enable_determinism
except Exception:  # pragma: no cover
    enable_determinism = None

def main():
    parser = argparse.ArgumentParser(description="Mix stems into a single track")
    parser.add_argument("input", help="input directory containing stems")
    parser.add_argument("output", help="output directory")
    parser.add_argument("--reference", help="optional reference track")
    parser.add_argument(
        "--seed",
        type=int,
        help="set random seed and enable deterministic backends",
    )
    args = parser.parse_args()
    if args.seed is not None and enable_determinism is not None:
        enable_determinism(args.seed)
    device = "cuda" if (torch and torch.cuda.is_available()) else "cpu"
    print(f"Using device: {device}")
    report = process(Path(args.input), Path(args.output), reference=args.reference)
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
