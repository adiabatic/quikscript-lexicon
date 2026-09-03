# Hacking

## Regenerating

```sh
make artifacts     # rewrite lexicon/
make preview       # rewrite the client's generated stylesheets
```

What keeps a stale `lexicon/` from being committed, and what a corpus bump involves, are in [`docs/pipeline.md`](docs/pipeline.md#regenerating).

## Proofs

```sh
make check         # lint, types, tests, validator, and artifact freshness
```

The validator verifies the corpus SHA-256 first, so a corpus bump is always a deliberate, reviewable change; it then makes one pass over the corpus and holds two row sets to account — the segment mapping over every row upstream ships, the spellings over the rows the lexicon spells. What it demands of each layer is stated by that layer’s own spec — [`docs/ipa-to-qs.md`](docs/ipa-to-qs.md), [Read’s orthographic rules](docs/orthographic-rules.md#what-the-validator-checks), [the word signs](docs/word-signs.md#what-the-validator-checks), and [`docs/validation.md`](docs/validation.md) for the specimen passages, the round trip and the Manual’s own lint — and why the pass splits at all, with what that costs, is in [`docs/pipeline.md`](docs/pipeline.md#where-the-validator-runs-and-why-it-splits).

## The language server

`editor/server/` is the `quikscript-lsp` server and `editor/vscode/` is a VS Code client for it. Neither is compiled, so trying them from a checkout takes an install and nothing else:

```sh
cd editor/vscode && npm ci     # `make check` does this for you
code --extensionDevelopmentPath="$PWD" ../..
```

That opens an Extension Development Host with the repo as its workspace folder, and the client launches `editor/server/server.js` over stdio; edits to the server take effect on the next reload. `make bundle` writes the single-file `editor/server/dist/quikscript-lsp` the protocol suite proves and BBEdit will launch, which the client prefers when one is bundled beside it.

To install into a normal VS Code rather than a development host, `make install-vsix` bundles the server into the extension, packages `dist/quikscript-vscode-<version>.vsix`, which carries its own server and so needs no checkout on the other end, and installs it over whatever copy is already there:

```sh
make install-vsix
```

It names the `.vsix` after the version in `editor/vscode/package.json`; reload any open window to pick the new build up. `make vsix` alone stops at the package, for handing the file to someone else:

```sh
make vsix
code --install-extension dist/quikscript-vscode-0.1.0.vsix
```

Two things otherwise read as breakage. Quikscript is Private Use Area text, so every spelling renders as a box until a Quikscript font is installed and `editor.fontFamily` points at it — the vendored `data/abbots-morton-spaceport/*.woff2` decompress to installable fonts with `woff2_decompress`, which names its CFF output `.ttf` where macOS wants `.otf`. That setting does not reach the Quick Fix menu or the Problems panel, which VS Code paints in the workbench UI font, so the fixes read as boxes there however the font is installed — the diagnostic message names them instead, which the squiggle hover and the `F8` peek both paint in `editor.fontFamily`, and the Quikscript panel beside Problems shows and applies them in a bundled face that needs no setting at all. And Latin-to-Quikscript completions stay off until `quikscript.completions` is set to `onDemand` or `auto`.
