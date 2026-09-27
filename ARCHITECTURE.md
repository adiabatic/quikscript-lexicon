# Layout

The files below are listed in the order a word passes through the pipeline.

- `data/readlex/` — the vendored ReadLex corpus, pinned by SHA-256 ([provenance](data/readlex/README.md)).
- `src/qslex/data/var-tags.tsv` — the row policy: which accent tags the lexicon spells and which it drops (spec: [`docs/pipeline.md`](docs/pipeline.md)).
- `src/qslex/data/ipa-quirks.tsv` — fixes for upstream ReadLex quirks, applied to the IPA before tokenization.
- `src/qslex/csur.py` — each Quikscript letter’s name and PUA codepoint. The mapping loader checks each mapping row’s letter names and codepoints against this table, and the lexicon JSON’s `letters` table is generated from it (spec: [`docs/conformance.md`](docs/conformance.md)).
- `src/qslex/data/ipa-to-qs.tsv` — the IPA → Quikscript segment mapping that the tokenizer matches against (spec: [`docs/ipa-to-qs.md`](docs/ipa-to-qs.md)).
- `src/qslex/data/ipa-overrides.tsv` — per-word stress overrides for ɪə, used where the mechanical rule gives the wrong result.
- `src/qslex/data/shavian-divergences.tsv` — words where the number of stressed rhotic ɪə the segment mapping writes differs from the number of EAR letters (𐑽) in ReadLex’s Shavian column. Most of them follow the Manual’s terminal -ier/-ior convention. The validator’s Shavian EAR cross-check expects these differences and fails on any other.
- `src/qslex/elements.py` — splits a hyphenated or multi-word entry into elements. The rules, the word signs and the lint checks all use this split, so they agree on where the boundaries are.
- `src/qslex/rules.py` — Read’s terminal, affix and prefix conventions, applied on top of the segment mapping to each element of a compound. It also produces the ·Excite/·Exam X-letter column, and it applies the n't elision to the senior column only (spec: [`docs/orthographic-rules.md`](docs/orthographic-rules.md)).
- `src/qslex/data/manual-spellings.tsv` — every spelling the Manual writes out, and every example word it names. The validator checks the rules’ output against these expected spellings.
- `src/qslex/data/rule-words.tsv` — per-word decisions for the five rules whose trigger the data cannot decide by itself.
- `src/qslex/data/x-decisions.tsv` — the words where the Latin `x` cannot be aligned to a letter pair mechanically.
- `src/qslex/words.py` — the lexical layer, which runs last. It applies the Manual’s word signs, standard word-outlines and abbreviations, and the junior forms where they differ (spec: [`docs/word-signs.md`](docs/word-signs.md)).
- `src/qslex/data/word-signs.tsv` — the core eight, the three abbreviations and every standard word-outline, with the junior form where it differs.
- `src/qslex/data/contractions.tsv` — the Manual’s §III Senior contractions, plus two forms the list omits: doing, which the terminal -ing section prints, and done, which the No-how passage writes. The build does not apply them to any spelling column. The transliterator writes every row except done, and the spelling checkers accept every whole-word row.
- `src/qslex/added.py` and `src/qslex/data/added-words.tsv` — words the corpus does not have, including the alphabet’s own name. Each is a row in the same format as a corpus row. The rows are appended after the row policy and spelled by the same rules, and each row records the spelling those rules must give it (spec: [`docs/pipeline.md`](docs/pipeline.md#words-the-corpus-lacks)).
- `src/qslex/build.py` — writes `lexicon/`. It prints the number of rows converted, skipped and added, and how many rows have a junior or X-letter spelling.
- `src/qslex/data/manual-passages.tsv` — the Manual’s eleven specimen passages, word by word. The finished spellings are checked against them (spec: [`docs/validation.md`](docs/validation.md)).
- `src/qslex/roundtrip.py` — the reverse of the segment mapping. It reads every spelling in the lexicon back to a phoneme string and compares it with the IPA it came from.
- `src/qslex/lint.py` — checks the finished spellings against the Manual’s conventions. Each check runs only where the Orthodox spelling contains the trigger for its rule. `src/qslex/data/lint-pragmas.tsv` lists any exceptions. Each row exempts one word from one check because of a known defect tracked in another issue.
- `src/qslex/latin2qs.py` — the transliterator: a port of ReadLex’s `latin2shaw.py` that turns running Latin text into Quikscript (spec: [`docs/latin2qs.md`](docs/latin2qs.md)).
- `src/qslex/checker_data.py` — computes the data every spelling checker uses: the set of accepted spellings with their frequencies, and the suggestion tables. It also compares the word set and the TRY letter order with the hunspell `.dic` and `.aff` in `lexicon/`.
- `src/qslex/desk.py` — generates the Quikscript Desk page, `site/index.html`. The page is one self-contained file: the checker data, the vendored fonts and the vendored Markdown parser are all inlined.
- `src/qslex/payload.py` — writes the same checker data to `editor/server/payload.json` for the `quikscript-lsp` language server. It adds two lookup maps that only the server uses:
  - `latin_by_spelling` maps each accepted Quikscript spelling to the Latin word, tag and column of each entry with that spelling. Hover, the diagnostic messages and `quikscript/fixes` use it to show the Latin word a spelling stands for.
  - `spellings_by_latin` maps each lowercased Latin word to its entries’ tags, frequencies and spelling columns. Completions and `quikscript/spellings` use it, and hover uses it to show an entry’s spellings in the other columns.

  The file is committed, and `make check` fails if it differs from a fresh build.
- `src/qslex/preview.py` — writes the two stylesheets that let the VS Code client show Quikscript. Each inlines the vendored Sans Senior fonts as data URIs, as the Desk page does. The `@font-face` rules have a `unicode-range` of U+E650–E67E, the Quikscript letters in the Private Use Area, so Latin text keeps the reader’s font. Both files are committed, and `make check` fails if either differs from a fresh build.
  - `media/quikscript-preview.css` is for the Markdown preview. The preview draws prose in the Markdown font, which has no Quikscript glyphs. Code spans already use `--vscode-editor-font-family`, so the stylesheet leaves them alone.
  - `media/quikscript-webview.css` is for the Fixes panel’s webview, which falls back to the workbench font instead. The inlined fonts load only because the panel’s page lists `data:` in its Content-Security-Policy `font-src`.
- `editor/server/` — the `quikscript-lsp` language server. It is plain JavaScript with JSDoc types, and `tsc --noEmit` checks them against `vscode-languageserver`’s declarations. It imports the Desk’s `src/qslex/web/core.js`, unmodified, to tokenize, check and suggest, and it communicates over stdio. It provides:
  - diagnostics, with quick fixes in the order `suggest()` returns them;
  - ignores, stored in `.quikscript-ignore` files in the document’s directory and each directory above it, and in the user file `${XDG_CONFIG_HOME:-~/.config}/quikscript/ignore`;
  - hover, which shows the Latin word for a Quikscript token;
  - Latin→Quikscript completions, controlled by `quikscript.completions` (`off`, `onDemand` or `auto`; `off` by default). The server reads the setting from `initializationOptions` and from a `workspace/configuration` request;
  - `quikscript/fixes`, which returns each flagged word’s suggestions, their Latin glosses, their edits and the word’s ignore commands in one response, for a client that can show and apply them;
  - `quikscript/spellings`, which returns the Quikscript spellings of each Latin word in a text.

  VS Code draws the Quick Fix menu and the Problems panel in the workbench UI font, so Quikscript cannot be read there. The server works around this in two places that VS Code draws in `editor.fontFamily`. Hover puts each spelling in a fenced code block, the only part of a hover drawn in that font. Each diagnostic’s message lists the fixes and the Latin word each one spells, because the squiggle hover and the `F8` peek show the message in that font.

  The server reads `payload.json`, which `src/qslex/payload.py` generates. `make bundle` writes the server as a single file to `editor/server/dist/quikscript-lsp`. The protocol tests bundle their own copy into a scratch directory under `tmp/` and run it over stdio, so every `make check` tests a freshly bundled server. `make vsix` bundles another copy into the VS Code extension.
- `editor/vscode/` — the VS Code client for that server. It is plain JavaScript, type-checked by `tsc --noEmit` against the VS Code API’s declarations. It launches the server over stdio for Markdown and plain text files, and contributes the `quikscript.completions` and `quikscript.serverPath` settings.
  - It adds a Fixes view to a Quikscript panel beside Problems. The view is a webview built from `quikscript/fixes`. It lists the active document’s flagged words, with each suggestion as a button in the vendored Senior font beside its Latin gloss. A fix is applied through `workspace.applyEdit`, and an ignore through the server’s commands.
  - A Latin box at the top of the view and one in each flagged word’s section send the typed word to `quikscript/spellings`. The top box copies the spelling that is clicked, and a section’s box applies it.
  - The view model is `lib/panel.js`, tested by `node --test`. The webview’s own script is `media/panel.js`.
  - The extension uses the server named by `quikscript.serverPath` if it is set, then `dist/quikscript-lsp` inside the extension if there is one, then `editor/server/server.js` in the checkout. `make vsix` writes `dist/quikscript-lsp` and packages it, so an installed extension has its own server.
  - It contributes the generated `media/quikscript-preview.css` as a `markdown.previewStyles` entry, and the Fixes panel loads the generated `media/quikscript-webview.css`.
- `src/qslex/` — the loaders, the tokenizer and the validator, which checks every layer above.

The mapping tables are inside the package so they can be imported from an installed wheel. The corpus is outside it, because a program that transcribes IPA does not need 27 MB of ReadLex.
