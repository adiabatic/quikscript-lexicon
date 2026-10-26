# Vendored marked

`marked.umd.js` is an unmodified copy of the file from the published [marked](https://github.com/markedjs/marked) tarball. It is vendored so that [`site/index.html`](../../site/index.html) can be rebuilt from a clean checkout without network access. The page inlines it in its own `<script>` element, so the page also works from a `file:` URL with nothing else installed.

|                 |                                                                                             |
| --------------- | ------------------------------------------------------------------------------------------- |
| Upstream        | <https://github.com/markedjs/marked>                                                        |
| Version         | 18.0.7                                                                                      |
| Tarball         | <https://registry.npmjs.org/marked/-/marked-18.0.7.tgz>, member `package/lib/marked.umd.js` |
| Tarball SHA-256 | `edcb08b6a56e5bfa9a1177a29943f19587771297e123694134d166546e1201b6`                          |
| SHA-256         | `7a1f8c5e7226b75ff16644bdb2c0130d2ae7371e7ea3106c2d6dac77ab0ff7b6`                          |
| License         | MIT, © 2018+ MarkedJS, © 2011–2018 Christopher Jeffrey. See [`LICENSE`](LICENSE).           |

## Why the UMD build

The package’s entry point, `lib/marked.esm.js`, is an ES module, and an ES module cannot be inlined for this page. An inline `<script type="module">` has no URL, so no other script can import from it. Loading the module from a separate file fails from a `file:` URL, because browsers apply CORS to module scripts. The UMD build defines a `marked` global from an ordinary inline `<script>`, which works in a single-file offline page. Both builds are generated from the same source in the same release.

The tarball’s digest is recorded as well as the file’s because the tarball is what npm publishes, so it can be downloaded again and compared. The file is one member of it.

## Bumping it

`src/qslex/desk.py` records the file’s SHA-256 and checks it before inlining the file, so replacing the file fails the build until the recorded SHA-256 is updated to match. To bump marked:

1. Replace the file.
2. Update the digests here and in `src/qslex/desk.py`.
3. Run `make site`, then `make check`.
