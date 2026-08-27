"""The CLI help surface must format without raising.

argparse runs `help_string % params` on every action's help text, so a bare `%` in a help
string (e.g. "READY 80%") breaks `--help` at runtime while every subcommand still works —
a trap that hides until someone runs `--help`. This pure test formats the top-level parser
and every subparser so a stray `%` is caught in CI, not in the field. No DB needed.
"""
from __future__ import annotations

from app.cli import build_parser


def test_top_level_help_formats():
    build_parser().format_help()          # raises ValueError on an unescaped '%'


def test_every_subparser_help_formats():
    parser = build_parser()
    subparsers = [a for a in parser._actions if hasattr(a, "choices") and a.choices]
    seen = 0
    for sp in subparsers:
        for name, subparser in sp.choices.items():
            subparser.format_help()       # each subcommand's -h must format too
            seen += 1
    assert seen > 0                        # guard against silently testing nothing
