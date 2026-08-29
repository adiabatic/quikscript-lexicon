"""The VS Code client’s stylesheets, carrying the face neither surface can otherwise reach.

editor/vscode/media/quikscript-preview.css and editor/vscode/media/quikscript-webview.css are generated, never hand-edited: the same two `@font-face` rules with the vendored Senior faces inlined as data URIs, and one rule putting that family ahead of the font the surface would paint prose in. VS Code paints Markdown preview prose in the Markdown font and a webview in the workbench font, and no Quikscript face is part of either, so every spelling is a box without this; a code span already resolves through `--vscode-editor-font-family` and is left alone. The rules are scoped by `unicode-range` to the Private Use Area block, so Latin keeps whatever font the reader chose and only Quikscript falls through. The webview is a file of its own rather than a copy of the preview’s because it differs at both ends: it falls back to the workbench font, and it paints the block only through fonts its own page delivers, whose data URIs its page must name in a `font-src` of its own Content-Security-Policy — where the preview’s policy already allows them. Inlining rather than shipping the files beside the stylesheets is what keeps the extension’s copy of a face from drifting from the vendored one, and makes a stale stylesheet a freshness failure rather than a discovery.
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
    """The `@font-face` rules both stylesheets open with, one per vendored face."""
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
    """The preview stylesheet as the file carries it: the faces, then the one rule using them."""
    root = root if root is not None else repo_root()
    blocks = faces(root)
    blocks.append(f"html,\nbody {{\n  font-family: '{FAMILY}', {MARKDOWN_STACK};\n}}\n")
    return "\n".join(blocks)


def panel(root: Path | None = None) -> str:
    """The webview stylesheet: the same faces, ahead of the workbench font a panel is painted in."""
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
