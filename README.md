# Quikscript lexicon

This started out as [Shavian-info/readlex](https://github.com/Shavian-info/readlex), but for Quikscript.

Now it’s a repository for all kinds of things that depend on knowing how to spell Quikscript properly, or at least reasonably well.

The most user-facing things here are:

- the [Quikscript Desk](#desk), a Markdown-aware Quikscript spell checker that runs in your browser (entirely locally if you want, without even a webserver)
- `quikscript-lsp`, a Quikscript spell-checking language server, with a VS Code extension that uses it ([setup](HACKING.md#the-language-server))

The rest of the README mostly describes things in the order of the underlying data pipeline, which mostly ends up being sorted from “most nerdy” to “least nerdy”.

## The lexicon

Generated into [`lexicon/`](lexicon) and committed, so you can just use them without building anything:

- [`lexicon/quikscript-lexicon.json`](lexicon/quikscript-lexicon.json) — every entry, grouped by headword

The other files are generated in the same build, from the same entries:

- [`lexicon/quikscript-lexicon.tsv`](lexicon/quikscript-lexicon.tsv) — one row per entry, with duplicate rows removed
- [`lexicon/qs_converter_phrases.txt`](lexicon/qs_converter_phrases.txt) — entries a tokenizer must match whole
- [`lexicon/en-Qaas.dic`](lexicon/en-Qaas.dic) and [`lexicon/en-Qaas.aff`](lexicon/en-Qaas.aff) — a Hunspell spelling dictionary; check Quikscript text with `hunspell -i utf-8 -d lexicon/en-Qaas`

There are three spelling columns. **`qs`** is Senior, the default. **`qs_junior`** and **`qs_x`** (the ·Excite/·Exam X-letter form) are filled in only where they differ from `qs`. [`lexicon/README.md`](lexicon/README.md) explains the columns, and [`docs/pipeline.md`](docs/pipeline.md) specifies the build.

## Layout

What each file is, in the order a word passes through the pipeline, is in [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Transliterating

```sh
uv run python -m qslex.latin2qs < input.txt              # Senior: ·Excite, ·Exam; “been” as ·Bay·No, etc.
uv run python -m qslex.latin2qs --junior in.txt          # Junior: neither
uv run python -m qslex.latin2qs --no-x-letters in.txt # Senior, but without either ·Excite or ·Exam
```

Senior is the default and writes both of the Manual’s Senior facilities. `--junior` writes neither. Each facility also has its own switch, `--x-letters`/`--no-x-letters` and `--contractions`/`--no-contractions`. The grade sets their defaults, and the switches override those defaults.

spaCy tokenizes and tags the text, and the spellings come from `lexicon/quikscript-lexicon.json`. The part-of-speech tag chooses between heteronyms. Namer dots, apostrophes and punctuation follow the Manual’s conventions. A word the lexicon lacks is either built from affixes and marked ⚠️, or passed through unchanged and marked ✢. The spec, the grades and the differences from upstream’s `latin2shaw.py` are in [`docs/latin2qs.md`](docs/latin2qs.md).

## Desk

[`site/index.html`](site/index.html) is a spell checker built on the lexicon. You type Markdown in one pane and read it set in Quikscript in the other. Every Quikscript word the lexicon does not accept gets a dotted red underline. Click it for suggestions, which edit the Markdown source. You can also ignore that one occurrence, or ignore the word everywhere. The page remembers ignored words in this browser’s `localStorage` when it is available.

A toggle button switches between the Junior and Senior fonts. It changes only the font. The accepted spellings are always the same: every spelling in the lexicon, plus the Manual’s Senior contractions, which the build does not write into any spelling column.

```sh
make site          # rewrite site/index.html
```

Then open the file. There is nothing to install and no server to run, and the page makes no network requests. The word list, [marked](https://github.com/markedjs/marked) and five [Abbots Morton Spaceport](https://github.com/adiabatic/abbots-morton-spaceport) fonts are all inlined in it. Those fonts are pixel fonts, so every font size the page sets is a multiple of 11px.

## Technically-released but unadvertised things

There are other things in this repository too, but I’m not yet ready to put my seal of <del>quality</del> adequacy on them, so I’m not mentioning them in this README.

## Hacking

[`HACKING.md`](HACKING.md) explains how to regenerate `lexicon/`, what `make check` tests at each layer, and how to run the language server.

## License

MIT — see [`LICENSE.md`](LICENSE.md). The vendored corpus under `data/readlex/`, and everything under `lexicon/` derived from it, is separately licensed, also MIT, © 2024 Shavian-info.
