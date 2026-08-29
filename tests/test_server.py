"""The editor server's checks, driven from pytest so `make check` runs them.

The node-side suite is the load-bearing proof of the editor work: `tsc --noEmit` holds the server's JSDoc types to the LSP library's own declarations, and the protocol tests bundle the server and speak real LSP over stdio to the exact artifact BBEdit will launch. The VS Code client is plain JavaScript on the same terms, held to the editor API's own declarations by the same typecheck, with the fixes panel's view model proved by its own `node --test` suite. All of it needs node; like the Desk page's tests, everything here is skipped when it is not on PATH.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

from qslex.readlex import repo_root

ROOT = repo_root()
EDITOR = ROOT / "editor"
SERVER = EDITOR / "server"
CLIENT = EDITOR / "vscode"
NODE = shutil.which("node")
NPM = shutil.which("npm")

pytestmark = pytest.mark.skipif(
    NODE is None or NPM is None, reason="node or npm is not on PATH"
)


def run(where: Path, *command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command), cwd=where, capture_output=True, text=True, check=False
    )


def report(name: str, finished: subprocess.CompletedProcess[str]) -> None:
    if finished.returncode:
        pytest.fail(
            f"{name} exited {finished.returncode}\n{finished.stdout}{finished.stderr}"
        )


def install(where: Path) -> Path:
    """node_modules matching the lockfile, installed only when absent or stale."""
    assert NPM is not None
    marker = where / "node_modules" / ".package-lock.json"
    lock = where / "package-lock.json"
    if not marker.is_file() or marker.stat().st_mtime < lock.stat().st_mtime:
        report(
            f"npm ci in {where.name}", run(where, NPM, "ci", "--no-audit", "--no-fund")
        )
    return where


@pytest.fixture(scope="module")
def installed() -> Path:
    return install(SERVER)


@pytest.fixture(scope="module")
def client() -> Path:
    return install(CLIENT)


def test_the_server_typechecks_against_the_lsp_librarys_declarations(
    installed: Path,
) -> None:
    assert NPM is not None
    report("tsc --noEmit", run(installed, NPM, "run", "check"))


def test_the_node_suite_proves_the_bundled_server_over_stdio(installed: Path) -> None:
    assert NPM is not None
    report("node --test", run(installed, NPM, "test"))


def test_the_vscode_client_typechecks_against_the_editor_apis_declarations(
    client: Path,
) -> None:
    assert NPM is not None
    report("tsc --noEmit", run(client, NPM, "run", "check"))


def test_the_client_suite_proves_the_panels_view_model(client: Path) -> None:
    assert NPM is not None
    report("node --test", run(client, NPM, "test"))
