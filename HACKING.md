# Hacking

## Regenerating

```sh
make artifacts     # rewrite lexicon/
make site          # rewrite site/index.html
make payload       # rewrite editor/server/payload.json
make preview       # rewrite the VS Code client's generated stylesheets
```

[`docs/pipeline.md`](docs/pipeline.md#regenerating) explains how `make check` catches an out-of-date `lexicon/`, and what a corpus bump involves.

## Checks

```sh
make check         # lint, type checks, tests, the validator, and a rebuild compared with every committed artifact
```

`make check` also runs the editor code’s `tsc --noEmit` and `node --test` suites through `tests/test_server.py`. That file skips them when `node` or `npm` is not on PATH.

The validator first verifies the corpus’s SHA-256, so replacing the file fails the build until the recorded SHA-256 is updated to match. It then makes one pass over the corpus and checks two different sets of rows. The segment mapping is checked against every row upstream ships, and the spellings against the rows the lexicon spells. Each layer’s spec says what the validator checks for it:

- [`docs/ipa-to-qs.md`](docs/ipa-to-qs.md) for the segment mapping
- [Read’s orthographic rules](docs/orthographic-rules.md#what-the-validator-checks)
- [the word signs](docs/word-signs.md#what-the-validator-checks)
- [`docs/validation.md`](docs/validation.md) for the specimen passages, the round trip and the lint checks based on the Manual’s conventions

[`docs/pipeline.md`](docs/pipeline.md#where-the-validator-runs-and-why-it-splits) explains why the pass checks two sets of rows, and what that split gives up.

## The language server

`editor/server/` is the `quikscript-lsp` server and `editor/vscode/` is a VS Code client for it. Neither is compiled, so to try them from a checkout you only need to install their dependencies:

```sh
cd editor/server && npm ci && cd ../vscode && npm ci   # `make check` runs both installs for you
code --extensionDevelopmentPath="$PWD" ../..
```

That opens an Extension Development Host with the repository as its workspace folder. The client launches `editor/server/server.js` over stdio, and edits to the server take effect when you reload the window. If `editor/vscode/dist/quikscript-lsp` exists, the client launches that bundle instead, and edits to the server sources have no effect until you delete it. `make vsix` writes that file. A `quikscript.serverPath` setting takes precedence over both.

`make bundle` writes the server as a single file, `editor/server/dist/quikscript-lsp`, which any LSP client, such as BBEdit, can launch with `--stdio`. The VS Code client does not look for this file. Set `quikscript.serverPath` to use it.

To install into a normal VS Code instead of a development host, run `make install-vsix`. It bundles the server into the extension, packages `dist/quikscript-vscode-<version>.vsix`, and installs it over any copy that is already installed. The package contains its own server, so it does not need a checkout.

```sh
make install-vsix
```

The `.vsix` is named after the version in `editor/vscode/package.json`. Reload any open window to load the new build. `make vsix` stops after packaging, for when you want to give the file to someone else:

```sh
make vsix
code --install-extension dist/quikscript-vscode-0.1.0.vsix
```

Three behaviors can look like bugs:

- Quikscript is Private Use Area text, so every spelling displays as a box until a Quikscript font is installed and `editor.fontFamily` names it. `woff2_decompress` turns the vendored `data/abbots-morton-spaceport/*.woff2` files into installable fonts. It names its CFF output `.ttf`, but macOS expects `.otf`.
- `editor.fontFamily` does not apply to the Quick Fix menu or the Problems panel, which VS Code draws in the workbench UI font. The fixes show as boxes there, whatever font is installed. The diagnostic message lists them instead, and the squiggle hover and the `F8` peek draw that message in `editor.fontFamily`. The Quikscript panel beside Problems also shows and applies the fixes, in a bundled font that needs no setting.
- Latin-to-Quikscript completions are off until `quikscript.completions` is set to `onDemand` or `auto`.
