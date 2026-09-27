"""The editor's JavaScript checks, run from pytest so that `make check` runs them.

These are the main tests of the editor work. In editor/server, `tsc --noEmit` type-checks the server's JSDoc types against the LSP library's declarations, and `node --test` runs the server's test files. The protocol tests among them bundle the server into a scratch directory with `bundle.js`, the code `make bundle` uses, and send it LSP messages over stdio. The VS Code client in editor/vscode is also JavaScript with JSDoc types. Its own `tsc --noEmit` run checks it against the VS Code API's declarations, and its `node --test` suite tests the Fixes panel's view model. Everything here needs node and npm and is skipped when either is not on PATH, as the Desk page's node tests are skipped without node.
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
