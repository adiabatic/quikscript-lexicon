"""The editor server's checks, driven from pytest so `make check` runs them.

The node-side suite is the load-bearing proof of the editor work: `tsc --noEmit` holds the server's JSDoc types to the LSP library's own declarations, and the protocol tests bundle the server and speak real LSP over stdio to the exact artifact BBEdit will launch. Both need node; like the Desk page's tests, everything here is skipped when it is not on PATH.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

from qslex.readlex import repo_root

ROOT = repo_root()
SERVER = ROOT / "editor" / "server"
NODE = shutil.which("node")
NPM = shutil.which("npm")

pytestmark = pytest.mark.skipif(
    NODE is None or NPM is None, reason="node or npm is not on PATH"
)


def run(*command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command), cwd=SERVER, capture_output=True, text=True, check=False
    )


def report(name: str, finished: subprocess.CompletedProcess[str]) -> None:
    if finished.returncode:
        pytest.fail(
            f"{name} exited {finished.returncode}\n{finished.stdout}{finished.stderr}"
        )


@pytest.fixture(scope="module")
def installed() -> Path:
    """node_modules matching the lockfile, installed only when absent or stale."""
    assert NPM is not None
    marker = SERVER / "node_modules" / ".package-lock.json"
    lock = SERVER / "package-lock.json"
    if not marker.is_file() or marker.stat().st_mtime < lock.stat().st_mtime:
        report("npm ci", run(NPM, "ci", "--no-audit", "--no-fund"))
    return SERVER


def test_the_server_typechecks_against_the_lsp_librarys_declarations(
    installed: Path,
) -> None:
    assert NPM is not None
    report("tsc --noEmit", run(NPM, "run", "check"))


def test_the_node_suite_proves_the_bundled_server_over_stdio(installed: Path) -> None:
    assert NPM is not None
    report("node --test", run(NPM, "test"))
