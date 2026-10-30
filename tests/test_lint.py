"""(Agg. 71) Il codice non ha nomi non definiti né import inutili (se ruff è installato)."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.skipif(shutil.which("ruff") is None, reason="ruff non installato (pip install ruff)")
def test_ruff_clean():
    r = subprocess.run(["ruff", "check", "engine", "--no-cache"], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-3000:]
