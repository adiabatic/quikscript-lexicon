# Quikscript for VS Code

Spell-checks [Quikscript](https://quikscript.net/) in Markdown and plain text files. It provides:

- diagnostics as you type;
- quick fixes, in the order `suggest()` returns them (the Quikscript Desk uses the same function);
- a list of those fixes, with the Latin word each one spells, in each diagnostic’s message;
- a Fixes panel that shows each suggestion in a bundled Quikscript font and applies it on a click;
- hover, which shows the Latin word for a Quikscript spelling;
- optional Latin-to-Quikscript completions.

Rendered Markdown previews use a bundled Quikscript font, so Quikscript in a preview displays without any setting.

## Fonts

Quikscript is Private Use Area text. Install a Quikscript font and set `editor.fontFamily` to it, or every spelling displays as a box. `editor.fontFamily` applies to the editor, the completion list, fenced blocks in a hover, and both places a diagnostic is shown: the hover over the squiggle and the View Problem peek (`F8`).

It does not apply to the Quick Fix menu or the Problems panel. VS Code draws both in the workbench UI font, and no setting changes that font. That is why the diagnostic message lists the fixes: hover a misspelling, or press `F8`, to read them.

The Fixes panel, beside Problems, needs no font setting. It uses the Abbots Morton Spaceport Sans Senior font bundled with the extension. For each flagged word, the panel shows:

- each suggestion as a button, with its Latin gloss;
- a “(N)” button beside a suggestion when the same misspelling occurs N more times in the file, which fixes every occurrence;
- a box for typing the word in Latin letters, for when the right word is not among the suggestions. The spellings it shows work like suggestions and have the same “(N)” button;
- buttons for each ignore scope.

The box at the top of the panel also takes Latin letters. It shows the Quikscript spellings, and clicking a spelling copies it to the clipboard.

## Settings

- `quikscript.completions`: `off` (the default), `onDemand`, or `auto`.
- `quikscript.serverPath`: the path to a `quikscript-lsp` to use instead of the packaged one. When empty, the extension uses the bundled `dist/quikscript-lsp`, then `editor/server/server.js` when the extension runs from a checkout of this repository.

## Ignoring words

Words can be ignored by listing them, one per line, in a `.quikscript-ignore` file in the document’s directory or any directory above it, or in the user file `${XDG_CONFIG_HOME:-~/.config}/quikscript/ignore`. The quick fixes and the Fixes panel provide four ignore scopes:

- this occurrence, for the current session only (nothing is written to a file);
- the document’s directory;
- the workspace folder that contains the document;
- the user file.

The directory scope is not shown when the document’s directory is the workspace folder itself, because both scopes would write the same file. For a file outside every workspace folder, the file’s directory is used as the workspace folder.
