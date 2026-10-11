"""Executa os testes Node da Pages Function da lista de espera."""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")


@pytest.mark.skipif(NODE is None, reason="Node.js não instalado; a função roda na Cloudflare")
def test_waitlist_pages_function_node_suite():
    result = subprocess.run(
        [NODE, "--test", str(ROOT / "tests" / "js" / "lista-de-espera.test.mjs")],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=120,
    )

    assert result.returncode == 0, result.stdout + result.stderr
