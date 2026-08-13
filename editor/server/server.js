const { createConnection, TextDocumentSyncKind } = require("vscode-languageserver/node");
const data = require("./payload.json");
const { lexicon } = require("./lib/lexicon.js");
const { CAP, diagnostics } = require("./lib/check.js");
const { debouncer } = require("./lib/debounce.js");

const DELAY = 200;

const connection = createConnection();
const words = lexicon(data);
/** @type {Map<string, {text: string, languageId: string, version: number}>} */
const documents = new Map();
const pending = debouncer(DELAY, publish);

/** @param {string} uri */
function publish(uri) {
  const held = documents.get(uri);
  if (!held) return;
  const found = diagnostics(held.text, held.languageId, words.active);
  if (found.length >= CAP) {
    connection.console.log(`quikscript-lsp: diagnostics capped at ${CAP} for ${uri}`);
  }
  connection
    .sendDiagnostics({ uri, version: held.version, diagnostics: found })
    .catch(() => {
      process.stderr.write(`quikscript-lsp: failed to publish diagnostics for ${uri}\n`);
    });
}

connection.onInitialize(() => ({
  capabilities: {
    textDocumentSync: { openClose: true, change: TextDocumentSyncKind.Full },
  },
  serverInfo: { name: "quikscript-lsp" },
}));

connection.onInitialized(() => {
  connection.console.log(`quikscript-lsp: ${words.active.size} spellings loaded`);
});

connection.onDidOpenTextDocument(({ textDocument }) => {
  documents.set(textDocument.uri, {
    text: textDocument.text,
    languageId: textDocument.languageId,
    version: textDocument.version,
  });
  pending.schedule(textDocument.uri);
});

let warned = false;

connection.onDidChangeTextDocument(({ textDocument, contentChanges }) => {
  const held = documents.get(textDocument.uri);
  if (!held) return;
  let whole = false;
  for (const change of contentChanges) {
    if ("range" in change) continue;
    held.text = change.text;
    whole = true;
  }
  if (!whole) {
    if (!warned) {
      warned = true;
      connection.console.warn(
        "quikscript-lsp: ignoring ranged changes; only full-document sync is spoken",
      );
    }
    return;
  }
  held.version = textDocument.version;
  pending.schedule(textDocument.uri);
});

connection.onDidCloseTextDocument(({ textDocument }) => {
  pending.cancel(textDocument.uri);
  documents.delete(textDocument.uri);
  connection
    .sendDiagnostics({ uri: textDocument.uri, diagnostics: [] })
    .catch(() => {});
});

connection.onShutdown(() => {
  pending.clear();
  documents.clear();
});

connection.listen();
