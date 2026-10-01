"""Command-line arguments for scripts run as ``blender -b --python <script> -- <args>``."""
import argparse
import sys


def script_args(parser: argparse.ArgumentParser) -> argparse.Namespace:
    """Parse only the arguments after ``--`` (Blender consumes everything before it)."""
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_args(argv)
