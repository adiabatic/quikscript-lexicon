# Quikscript for VS Code

Spell-checks [Quikscript](https://quikscript.net/) in Markdown and plain text: diagnostics as you type, quick fixes in the Quikscript Desk's order, hover to read a spelling back to its Latin, and optional Latin-to-Quikscript completions.

Quikscript is Private Use Area text, so install a Quikscript font and point `editor.fontFamily` at it or every spelling renders as a box.

## Settings

- `quikscript.completions` — `off` (the default), `onDemand`, or `auto`.
- `quikscript.serverPath` — path to a `quikscript-lsp` other than the one packaged here.

Words can be excused in a `.quikscript-ignore` file beside the document or at the workspace root, or in the user file under `${XDG_CONFIG_HOME:-~/.config}/quikscript`. The quick fixes write them for you.
