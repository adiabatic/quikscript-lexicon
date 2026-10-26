"""Builds the VS Code extension’s two stylesheets, which give the Markdown preview and the extension’s webview a Quikscript font.

editor/vscode/media/quikscript-preview.css and editor/vscode/media/quikscript-webview.css are generated and never edited by hand. Each has the same two `@font-face` rules, with the vendored Sans Senior faces inlined as data URIs. Each also has one rule that lists that family ahead of the font the surface would otherwise use for prose.

VS Code renders Markdown preview prose in the Markdown font and a webview in the workbench font. Neither font has Quikscript letters, so without these stylesheets every spelling renders as a box. A code span already uses `--vscode-editor-font-family` and is left alone. The `@font-face` rules are limited by `unicode-range` to the Quikscript codepoints in the Private Use Area (U+E650–E67E), so Latin text keeps the reader’s font and only Quikscript uses these faces.

The webview has its own file for two reasons. Its fallback is the workbench font. It can also use only fonts that its own page supplies, so its page must allow their data URIs in the `font-src` of its own Content-Security-Policy. The preview’s policy already allows them.

The faces are inlined rather than shipped as files beside the stylesheets, so the extension always uses the vendored faces. `make check` runs `python -m qslex.preview --check`, which fails whenever a committed stylesheet differs from a rebuild.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from qslex.desk import FONT_DIR, FONTS, asset, data_uri
from qslex.readlex import repo_root

EDITOR = "editor"
VSCODE = "vscode"
MEDIA = "media"
PREVIEW = "quikscript-preview.css"
WEBVIEW = "quikscript-webview.css"

FAMILY = "Abbots Morton Spaceport Sans Senior"
FACES = (("400", "SANS_SENIOR_REGULAR"), ("700", "SANS_SENIOR_BOLD"))
BLOCK = "U+E650-E67E"
MARKDOWN_STACK = (
    "var(--markdown-font-family, -apple-system, BlinkMacSystemFont, "
    '"Segoe WPC", "Segoe UI", system-ui, "Ubuntu", "Droid Sans", sans-serif)'
)
WORKBENCH_STACK = "var(--vscode-font-family, sans-serif)"


def faces(root: Path) -> list[str]:
    """The `@font-face` rules both stylesheets start with, one for each Sans Senior weight in `FACES`."""
    return [
        "@font-face {\n"
        f"  font-family: '{FAMILY}';\n"
        f"  src: url('{data_uri(asset(FONT_DIR / FONTS[key], root))}') format('woff2');\n"
        f"  font-weight: {weight};\n"
        f"  unicode-range: {BLOCK};\n"
        "}\n"
        for weight, key in FACES
    ]


def build(root: Path | None = None) -> str:
    """The preview stylesheet: the faces, then the rule that uses them."""
    root = root if root is not None else repo_root()
    blocks = faces(root)
    blocks.append(f"html,\nbody {{\n  font-family: '{FAMILY}', {MARKDOWN_STACK};\n}}\n")
    return "\n".join(blocks)


def panel(root: Path | None = None) -> str:
    """The webview stylesheet: the same faces, listed ahead of the workbench font a webview uses."""
    root = root if root is not None else repo_root()
    blocks = faces(root)
    blocks.append(f"body {{\n  font-family: '{FAMILY}', {WORKBENCH_STACK};\n}}\n")
    return "\n".join(blocks)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Write the VS Code client’s stylesheets from the vendored faces"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="rebuild in memory and fail if what is on disk differs",
    )
    args = parser.parse_args(argv)

    media = repo_root() / EDITOR / VSCODE / MEDIA
    built = {PREVIEW: build(), WEBVIEW: panel()}
    if not args.check:
        media.mkdir(parents=True, exist_ok=True)
        for name, text in built.items():
            (media / name).write_text(text, encoding="utf-8", newline="\n")
            print(f"wrote {media / name}")
        print()
        for name, text in built.items():
            print(f"{name}: {len(FACES)} faces, {len(text.encode('utf-8'))} bytes")
        return 0

    stale: list[str] = []
    for name, text in built.items():
        path = media / name
        if not path.is_file():
            stale.append(f"{path} is missing")
        elif path.read_text(encoding="utf-8") != text:
            stale.append(f"{path} differs from a fresh build")
    for line in stale:
        print(line)
    if stale:
        print(f"\nFAILED: {len(stale)} artifact(s) out of date; run `make preview`")
        return 1
    print(f"OK: {len(built)} artifacts match a fresh build")
    return 0


if __name__ == "__main__":
    sys.exit(main())
