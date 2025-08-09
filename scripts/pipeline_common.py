#!/usr/bin/env python
"""Shared command-line interface for pipeline scripts."""
import argparse


def build_parser() -> argparse.ArgumentParser:
    """Create argument parser with unified options for all pipeline scripts."""
    parser = argparse.ArgumentParser(
        description="Run the audio processing pipeline (48 kHz/24-bit output)"
    )
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
