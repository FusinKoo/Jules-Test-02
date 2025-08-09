#!/usr/bin/env python
"""Shared command-line interface for pipeline scripts."""
import argparse
import os


def build_parser() -> argparse.ArgumentParser:
    """Create argument parser with unified options for all pipeline scripts."""
    parser = argparse.ArgumentParser(description="Run the audio processing pipeline")
    parser.add_argument("--input", required=True, help="input file or directory")
    parser.add_argument("--output", required=True, help="output directory")
    parser.add_argument("--rvc_model", help="path to the RVC model")
    parser.add_argument("--f0_method", default="rmvpe", help="pitch extraction method")
    parser.add_argument("--quality_profile", default="medium", help="quality/speed profile")
    parser.add_argument("--lufs_target", type=float, default=-14.0, help="target loudness in LUFS")
    parser.add_argument("--truepeak_margin", type=float, default=-1.0, help="true peak margin in dB")
    parser.add_argument("--dry_run", action="store_true", help="run without producing output")
    parser.add_argument(
        "--seed",
        type=int,
        help="set random seed and enable deterministic backends",
    )
    return parser


def resolve_rvc_model(args: argparse.Namespace) -> None:
    """Resolve and store the RVC model path.

    Updates ``args`` in place and propagates the result via the
    ``RVC_MODEL`` environment variable so downstream components can locate the
    model.
    """
    from mix.model_manager import get_model_path

    args.rvc_model = get_model_path(cli_path=args.rvc_model)
    os.environ["RVC_MODEL"] = args.rvc_model
