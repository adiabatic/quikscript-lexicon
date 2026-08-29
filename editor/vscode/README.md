# Quikscript for VS Code

Spell-checks [Quikscript](https://quikscript.net/) in Markdown and plain text: diagnostics as you type, quick fixes in the Quikscript Desk's order, each unknown spelling's diagnostic naming those fixes and what they read as, hover to read a spelling back to its Latin, and optional Latin-to-Quikscript completions. Rendered Markdown previews carry a Quikscript face of their own, so a preview reads without any setting at all.

Quikscript is Private Use Area text, so install a Quikscript font and point `editor.fontFamily` at it or every spelling renders as a box. That setting reaches the editor, the completion list, fenced blocks in a hover, and both places a diagnostic is shown — the hover over the squiggle and the View Problem peek on `F8`. It does not reach the Quick Fix menu or the Problems panel, which VS Code paints in the workbench UI font with no setting to change it. So the fixes are named in the diagnostic itself: hover a misspelling, or press `F8`, to read them before picking one from a menu that cannot show them.

## Settings

- `quikscript.completions` — `off` (the default), `onDemand`, or `auto`.
- `quikscript.serverPath` — path to a `quikscript-lsp` other than the one packaged here.

Words can be excused in a `.quikscript-ignore` file beside the document or at the workspace root, or in the user file under `${XDG_CONFIG_HOME:-~/.config}/quikscript`. The quick fixes write them for you.
