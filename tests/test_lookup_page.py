import shutil
import subprocess
from pathlib import Path

import pytest

from qslex.desk import SITE
from qslex.lookup_page import PAGE, build

NODE = shutil.which("node")
HERE = Path(__file__).resolve().parent
PAGE_TESTS, PAGE_CHECKS = "lookup_page.js", 6


@pytest.mark.skipif(NODE is None, reason="node is not on PATH")
def test_the_pages_three_scripts_run_together_over_a_shimmed_dom(
    tmp_path: Path,
) -> None:
    """The node file reads a fresh build rather than the committed `site/lookup.html`. `python -m qslex.lookup_page --check`, which `make check` runs, checks that the committed file matches a fresh build."""
    assert NODE is not None
    written = tmp_path / SITE / PAGE
    written.parent.mkdir()
    written.write_text(build(), encoding="utf-8", newline="\n")
    finished = subprocess.run(
        [NODE, str(HERE / PAGE_TESTS), str(written)],
        capture_output=True,
        text=True,
        check=False,
    )
    if finished.returncode:
        pytest.fail(
            f"{PAGE_TESTS} exited {finished.returncode}\n{finished.stdout}{finished.stderr}"
        )
    assert finished.stdout.splitlines()[-1] == f"{PAGE_CHECKS} checks passed", (
        finished.stdout
    )
