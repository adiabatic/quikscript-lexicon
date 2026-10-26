# Vendored Abbots Morton Spaceport fonts

The five `.woff2` files are unmodified copies from [adiabatic/abbots-morton-spaceport](https://github.com/adiabatic/abbots-morton-spaceport). They are vendored so that [`site/index.html`](../../site/index.html) and the VS Code extension’s stylesheets can be rebuilt from a clean checkout without network access. The page inlines each font as a `data:` URI, so the page also works from a `file:` URL with nothing else installed.

|          |                                                                                                                                                    |
| -------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| Upstream | <https://github.com/adiabatic/abbots-morton-spaceport>                                                                                             |
| Release  | [`release/16.000`](https://github.com/adiabatic/abbots-morton-spaceport/releases/tag/release%2F16.000), asset `abbots-morton-spaceport-16.000.zip` |
| License  | SIL OFL 1.1, © Nathan Galt, with glyphs from Departure Mono © 2022–2024 Helena Zhang. See [`LICENSE-OFL-1.1.txt`](LICENSE-OFL-1.1.txt).            |

| File                                            | SHA-256                                                            |
| ----------------------------------------------- | ------------------------------------------------------------------ |
| `AbbotsMortonSpaceportSansJunior-Regular.woff2` | `f2a997c4725a84b347040dae4ff776170152fb8c23f5fd35e04bff98c1dc2028` |
| `AbbotsMortonSpaceportSansJunior-Bold.woff2`    | `c788179a96b5fe0070f8c18d72c2021f87026b809940af7434e6a2636a9d7920` |
| `AbbotsMortonSpaceportSansSenior-Regular.woff2` | `09364498461369468ffa69c62f827581d096d6b45666705c94687f03d7bb70f8` |
| `AbbotsMortonSpaceportSansSenior-Bold.woff2`    | `088af65711523d3220e3449659f7404c4110bdefde7dd980bd6fa48d66eae316` |
| `AbbotsMortonSpaceportMono-Regular.woff2`       | `b4e9223937997b78ece9dcecbb3cfd8b4e0d1a9eaecde9316d74f8ae621e1a59` |

## Which font is used where

- **Sans Junior** draws each letter separately. **Sans Senior** joins letters. The Desk’s Junior/Senior toggle switches the preview and the fix popover between these two fonts. It does not change the spellings.
- **Sans Senior** is also the font the VS Code extension bundles for Markdown previews and the Fixes panel (see `src/qslex/preview.py`).
- **Mono** includes all of [Departure Mono](https://departuremono.com/) as well as the Quikscript letters. The Desk uses it on its own for the text area and for code. It is also the fallback after each Sans font in the Desk’s `font-family` lists, for characters the Sans fonts do not have.

Only these five files are vendored. The release also contains `.otf` files and a Mono Bold, which nothing here uses.

The page follows two rules from upstream’s README:

- Every font size on text that contains Quikscript is a multiple of 11px. The glyphs are pixel art, and other sizes blur them.
- Font smoothing is turned off with all three of `-webkit-font-smoothing: none`, `-moz-osx-font-smoothing: unset` and `font-smooth: never`.

The Bold weight is the Regular with a half-pixel overstrike. Upstream recommends 22px or larger for it, and the page uses Bold only at 22px or larger.

## Bumping it

`src/qslex/desk.py` records each file’s SHA-256 and checks it before inlining the file, so replacing the file fails the build until the recorded SHA-256 is updated to match. To bump the fonts:

1. Replace the files.
2. Update the digests here and in `src/qslex/desk.py`.
3. Run `make site` and `make preview`, then `make check`.
