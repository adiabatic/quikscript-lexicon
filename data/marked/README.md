# Vendored marked

`marked.umd.js` is vendored verbatim from the published [marked](https://github.com/markedjs/marked) tarball so that [`site/index.html`](../../docs/desk.md) is reproducible from a clean checkout, with no network access. The page inlines it in a `<script>` of its own, which is also what lets it work from a `file:` URL with nothing else installed.

|                 |                                                                                             |
| --------------- | ------------------------------------------------------------------------------------------- |
| Upstream        | <https://github.com/markedjs/marked>                                                        |
| Version         | 18.0.7                                                                                      |
| Tarball         | <https://registry.npmjs.org/marked/-/marked-18.0.7.tgz>, member `package/lib/marked.umd.js` |
| Tarball SHA-256 | `edcb08b6a56e5bfa9a1177a29943f19587771297e123694134d166546e1201b6`                          |
| SHA-256         | `7a1f8c5e7226b75ff16644bdb2c0130d2ae7371e7ea3106c2d6dac77ab0ff7b6`                          |
| Licence         | MIT, © 2018+ MarkedJS, © 2011–2018 Christopher Jeffrey — see [`LICENSE`](LICENSE)           |

## Why the UMD build

The package's own entry point is `lib/marked.esm.js`, and an ES module cannot be inlined: a `<script type="module">` with a body still needs a module scope, and loading one from a `file:` URL is blocked by CORS in every browser. The UMD build defines a `marked` global from an ordinary inline `<script>`, which is exactly what a single-file offline page needs. Both are generated from the same source in the same release, so this is a packaging choice and not a different library.

The tarball's digest is recorded beside the file's own because npm's published archive is the thing that can be re-fetched and compared; the file is one member of it.

## Bumping it

`src/qslex/desk.py` pins the file's digest above and verifies it before inlining, so a marked bump is a deliberate, reviewable change rather than a silent one: replace the file, update the digests here and in that module, then run `make site` and `make check`. The footer of the generated page names the version, so it moves too.
