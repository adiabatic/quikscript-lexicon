# Quikscript for VS Code

Spell-checks [Quikscript](https://quikscript.net/) in Markdown and plain text: diagnostics as you type, quick fixes in the Quikscript Desk's order, hover to read a spelling back to its Latin — or, on a misspelling, to read the fixes on offer — and optional Latin-to-Quikscript completions.

Quikscript is Private Use Area text, so install a Quikscript font and point `editor.fontFamily` at it or every spelling renders as a box. That setting reaches the editor, the completion list, and fenced blocks in a hover — which is why the hover writes every spelling in one. It does not reach the Quick Fix menu: VS Code paints that in the workbench UI font and offers no setting for it, so the fixes stay boxes there. Hover the misspelling to read them before picking one.

## Settings

- `quikscript.completions` — `off` (the default), `onDemand`, or `auto`.
- `quikscript.serverPath` — path to a `quikscript-lsp` other than the one packaged here.

Words can be excused in a `.quikscript-ignore` file beside the document or at the workspace root, or in the user file under `${XDG_CONFIG_HOME:-~/.config}/quikscript`. The quick fixes write them for you.
