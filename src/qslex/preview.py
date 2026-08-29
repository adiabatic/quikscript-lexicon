"""The Markdown preview’s stylesheet, carrying the face the preview cannot otherwise reach.

editor/vscode/media/quikscript-preview.css is generated, never hand-edited: two `@font-face` rules with the vendored Senior faces inlined as data URIs, and one rule putting that family ahead of the preview’s own. VS Code paints preview prose in the Markdown font, which no Quikscript font is part of, so every spelling in a rendered document is a box without this; a code span already resolves through `--vscode-editor-font-family` and is left alone. The rules are scoped by `unicode-range` to the Private Use Area block, so Latin keeps whatever font the reader chose and only Quikscript falls through. Inlining rather than shipping the files beside the stylesheet is what keeps the extension’s copy of a face from drifting from the vendored one, and makes a stale stylesheet a freshness failure rather than a discovery.
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
STYLESHEET = "quikscript-preview.css"

FAMILY = "Abbots Morton Spaceport Sans Senior"
FACES = (("400", "SANS_SENIOR_REGULAR"), ("700", "SANS_SENIOR_BOLD"))
BLOCK = "U+E650-E67E"
MARKDOWN_STACK = (
    "var(--markdown-font-family, -apple-system, BlinkMacSystemFont, "
    '"Segoe WPC", "Segoe UI", system-ui, "Ubuntu", "Droid Sans", sans-serif)'
)


def build(root: Path | None = None) -> str:
    """The stylesheet as the file carries it: the faces, then the one rule using them."""
    root = root if root is not None else repo_root()
    blocks = [
        "@font-face {\n"
        f"  font-family: '{FAMILY}';\n"
        f"  src: url('{data_uri(asset(FONT_DIR / FONTS[key], root))}') format('woff2');\n"
        f"  font-weight: {weight};\n"
        f"  unicode-range: {BLOCK};\n"
        "}\n"
        for weight, key in FACES
    ]
    blocks.append(f"html,\nbody {{\n  font-family: '{FAMILY}', {MARKDOWN_STACK};\n}}\n")
    return "\n".join(blocks)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Write the VS Code Markdown preview stylesheet from the vendored faces"
    )
    parser.add_argument(
        "--out", type=Path, default=repo_root() / EDITOR / VSCODE / MEDIA / STYLESHEET
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="rebuild in memory and fail if what is on disk differs",
    )
    args = parser.parse_args(argv)

    written = build()
    if not args.check:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(written, encoding="utf-8", newline="\n")
        print(f"wrote {args.out}")
        print()
        print(f"{len(FACES)} faces, {len(written.encode('utf-8'))} bytes")
        return 0

    stale = ""
    if not args.out.is_file():
        stale = f"{args.out} is missing"
    elif args.out.read_text(encoding="utf-8") != written:
        stale = f"{args.out} differs from a fresh build"
    if stale:
        print(stale)
        print("\nFAILED: 1 artifact(s) out of date; run `make preview`")
        return 1
    print("OK: 1 artifact matches a fresh build")
    return 0


if __name__ == "__main__":
    sys.exit(main())
