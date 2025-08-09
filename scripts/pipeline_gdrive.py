#!/usr/bin/env python
"""Google Drive variant of the processing pipeline."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline_common import build_parser

try:  # pragma: no cover - determinism optional
    from mix.deterministic import enable_determinism
except Exception:  # pragma: no cover - deterministic helper missing
    enable_determinism = None


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.seed is not None and enable_determinism is not None:
        enable_determinism(args.seed)
    if args.dry_run:
        print("Dry run: no processing performed")
        return
    from mix import process
    report = process(Path(args.input), Path(args.output))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
