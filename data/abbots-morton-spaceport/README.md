# Vendored Abbots Morton Spaceport fonts

The five `.woff2` files are vendored verbatim from [adiabatic/abbots-morton-spaceport](https://github.com/adiabatic/abbots-morton-spaceport) so that [`site/index.html`](../../docs/playground.md) is reproducible from a clean checkout, with no network access. The page inlines each one as a `data:` URI, which is also what lets it work from a `file:` URL with nothing else installed.

| | |
|---|---|
| Upstream | <https://github.com/adiabatic/abbots-morton-spaceport> |
| Release | [`release/16.000`](https://github.com/adiabatic/abbots-morton-spaceport/releases/tag/release%2F16.000), asset `abbots-morton-spaceport-16.000.zip` |
| Licence | SIL OFL 1.1, © Nathan Galt, with glyphs from Departure Mono © 2022–2024 Helena Zhang — see [`LICENSE-OFL-1.1.txt`](LICENSE-OFL-1.1.txt) |

| File | SHA-256 |
|---|---|
| `AbbotsMortonSpaceportSansJunior-Regular.woff2` | `f2a997c4725a84b347040dae4ff776170152fb8c23f5fd35e04bff98c1dc2028` |
| `AbbotsMortonSpaceportSansJunior-Bold.woff2` | `c788179a96b5fe0070f8c18d72c2021f87026b809940af7434e6a2636a9d7920` |
| `AbbotsMortonSpaceportSansSenior-Regular.woff2` | `09364498461369468ffa69c62f827581d096d6b45666705c94687f03d7bb70f8` |
| `AbbotsMortonSpaceportSansSenior-Bold.woff2` | `088af65711523d3220e3449659f7404c4110bdefde7dd980bd6fa48d66eae316` |
| `AbbotsMortonSpaceportMono-Regular.woff2` | `b4e9223937997b78ece9dcecbb3cfd8b4e0d1a9eaecde9316d74f8ae621e1a59` |

## Which face is which

Sans **Junior** is unligated and Sans **Senior** joins its letters, which is the grade the lexicon's `qs_junior` column records from the other side — so the playground's Junior/Senior toggle switches the face and the accepted spelling set together, and neither can drift from the other. **Mono** bundles the whole of [Departure Mono](https://departuremono.com/) alongside the Quikscript letters, so it stands alone as the textarea's face and sits behind Sans as its Latin fallback. Only the five faces the page loads are vendored; the release also ships `.otf`s and a Mono Bold, which nothing here uses.

Two rules from upstream's README that the page follows rather than reinvents: **every font size on Quikscript-bearing text is a multiple of 11px**, because the glyphs are pixels and anything else blurs them, and font smoothing is turned off with all three of `-webkit-font-smoothing: none`, `-moz-osx-font-smoothing: unset` and `font-smooth: never`. The Bold weight is a half-pixel overstrike of the Regular, which needs 22px or better to read — the size the page sets.

## Bumping it

`src/qslex/playground.py` pins each digest above and verifies it before inlining, so a font bump is a deliberate, reviewable change rather than a silent one: replace the files, update the digests here and in that module, then run `make site` and `make check`.
