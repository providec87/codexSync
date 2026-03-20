from __future__ import annotations

from pathlib import Path

# Allow running `python -m codexsync` from a source checkout without installing
# the package by extending package search path with src/codexsync.
_src_pkg = Path(__file__).resolve().parent.parent / "src" / "codexsync"
if _src_pkg.is_dir():
    __path__.append(str(_src_pkg))
