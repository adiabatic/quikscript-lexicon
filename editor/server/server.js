const path = require("node:path");
const { fileURLToPath } = require("node:url");
const { createConnection, TextDocumentSyncKind } = require("vscode-languageserver/node");
const data = require("./payload.json");
const { tokens } = require("../../src/qslex/web/core.js");
const { lexicon } = require("./lib/lexicon.js");
const { CAP, diagnostics, flagged, spot } = require("./lib/check.js");
const { debouncer } = require("./lib/debounce.js");
const { COMMANDS, OCCURRENCE, PROJECT, USER, actions, adviser } = require("./lib/actions.js");
const { above, ledger, projectIgnorePath, userIgnorePath } = require("./lib/ignores.js");

const DELAY = 200;
const BUDGET = 10000;
const PATIENCE = 500;

const connection = createConnection();
const words = lexicon(data);
const offered = adviser(words);
const files = ledger();
const userFile = userIgnorePath(process.env);
/** @type {Map<string, {text: string, languageId: string, version: number}>} */
const documents = new Map();
/** @type {Map<string, Set<string>>} */
const overlooked = new Map();
/** @type {string[]} */
let roots = [];
let inlined = false;
const pending = debouncer(DELAY, publish);

/** @param {string} uri */
function localPath(uri) {
  try {
    return fileURLToPath(uri);
  } catch {
    return null;
  }
}

/** @param {string} uri */
function projectRoot(uri) {
  const file = localPath(uri);
  if (!file) return roots[0] || null;
  const owned = roots.find((root) => file === root || file.startsWith(root + path.sep));
  return owned || path.dirname(file);
}

/** @param {string} uri */
function excusedFor(uri) {
  const file = localPath(uri);
  const home = file ? path.dirname(file) : roots[0];
  const sources = home ? above(home) : [];
  return files.read([...sources, userFile]);
}

/** @param {string} uri */
function overlookedFor(uri) {
  let held = overlooked.get(uri);
  if (!held) {
    held = new Set();
    overlooked.set(uri, held);
  }
  return held;
}

/** @param {string} word */
function spelled(word) {
  const runs = tokens(word);
  return runs.length === 1 && runs[0].start === 0 && runs[0].end === word.length;
}

/** @param {string} uri */
function checked(uri) {
  const held = documents.get(uri);
  if (!held) return null;
  const hits = flagged(
    held.text,
    held.languageId,
    words.active,
    excusedFor(uri),
    overlookedFor(uri),
  );
  const found = diagnostics(held.text, hits);
  const flags = hits.map((hit, at) => ({
    word: hit.word,
    occurrence: hit.occurrence,
    range: found[at].range,
  }));
  return { held, found, flags };
}

/**
 * @param {import("./lib/actions.js").Flag[]} flags
 * @returns {Map<string, import("./lib/check.js").Span[]>}
 */
function spanned(flags) {
  /** @type {Map<string, import("./lib/check.js").Span[]>} */
  const everywhere = new Map();
  for (const flag of flags) {
    const spans = everywhere.get(flag.word);
    if (spans) spans.push(flag.range);
    else everywhere.set(flag.word, [flag.range]);
  }
  return everywhere;
}

/**
 * @param {string} uri
 * @param {import("./lib/actions.js").Flag[]} flags
 * @param {Map<string, import("./lib/check.js").Span[]>} everywhere
 * @returns {import("./lib/actions.js").Action[][]}
 */
function crafted(uri, flags, everywhere) {
  const project = projectRoot(uri) !== null;
  const started = Date.now();
  /** @type {import("./lib/actions.js").Action[][]} */
  const out = [];
  let spent = 0;
  for (const flag of flags) {
    if (spent >= BUDGET || Date.now() - started >= PATIENCE) break;
    const built = actions(uri, flag, everywhere.get(flag.word) || [], offered(flag.word), project);
    out.push(built);
    for (const action of built) {
      spent += 1 + (action.edit ? action.edit.changes[uri].length : 0);
    }
  }
  return out;
}

/** @param {string} uri */
function publish(uri) {
  const result = checked(uri);
  if (!result) return;
  const { held, found, flags } = result;
  if (flags.length >= CAP) {
    connection.console.log(`quikscript-lsp: diagnostics capped at ${CAP} for ${uri}`);
  }
  if (inlined) {
    const lists = crafted(uri, flags, spanned(flags));
    for (const [at, built] of lists.entries()) found[at].codeActions = built;
    if (lists.length < flags.length) {
      connection.console.log(`quikscript-lsp: inline code actions truncated for ${uri}`);
    }
  }
  connection
    .sendDiagnostics({ uri, version: held.version, diagnostics: found })
    .catch(() => {
      process.stderr.write(`quikscript-lsp: failed to publish diagnostics for ${uri}\n`);
    });
}

/**
 * @param {import("./lib/check.js").Position} one
 * @param {import("./lib/check.js").Position} other
 * @returns {boolean}
 */
function precedes(one, other) {
  return one.line < other.line || (one.line === other.line && one.character < other.character);
}

/**
 * @param {import("./lib/check.js").Span} one
 * @param {import("./lib/check.js").Span} other
 * @returns {boolean}
 */
function touches(one, other) {
  return !precedes(one.end, other.start) && !precedes(other.end, one.start);
}

connection.onInitialize((params) => {
  const folders = params.workspaceFolders || [];
  roots = folders.map((folder) => localPath(folder.uri)).filter((held) => held !== null);
  if (roots.length === 0 && params.rootUri) {
    const root = localPath(params.rootUri);
    if (root) roots = [root];
  }
  roots.sort((one, other) => other.length - one.length);
  const published = /** @type {any} */ (params.capabilities.textDocument?.publishDiagnostics);
  inlined = Boolean(published && published.codeActionsInline);
  return {
    capabilities: {
      textDocumentSync: { openClose: true, change: TextDocumentSyncKind.Full },
      codeActionProvider: { codeActionKinds: ["quickfix"] },
      executeCommandProvider: { commands: COMMANDS },
    },
    serverInfo: { name: "quikscript-lsp" },
  };
});

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
  overlooked.delete(textDocument.uri);
  connection
    .sendDiagnostics({ uri: textDocument.uri, diagnostics: [] })
    .catch(() => {});
});

connection.onCodeAction(({ textDocument, range, context }) => {
  const only = context.only;
  if (only && !only.some((kind) => kind === "quickfix" || "quickfix".startsWith(kind + "."))) {
    return null;
  }
  const result = checked(textDocument.uri);
  if (!result) return null;
  const { flags } = result;
  const chosen = flags.filter((flag) => touches(flag.range, range));
  return crafted(textDocument.uri, chosen, spanned(flags)).flat();
});

connection.onExecuteCommand(({ command, arguments: args }) => {
  const asked = /** @type {{uri?: unknown, word?: unknown, occurrence?: unknown}} */ (
    (args && args[0]) || {}
  );
  const uri = typeof asked.uri === "string" && documents.has(asked.uri) ? asked.uri : null;
  const word = typeof asked.word === "string" && spelled(asked.word) ? asked.word : null;
  const count =
    typeof asked.occurrence === "number" &&
    Number.isInteger(asked.occurrence) &&
    asked.occurrence >= 0
      ? asked.occurrence
      : null;
  if (command === OCCURRENCE && uri && word && count !== null) {
    overlookedFor(uri).add(spot(word, count));
  } else if (command === PROJECT && uri && word) {
    const root = projectRoot(uri);
    if (!root) return null;
    files.append(projectIgnorePath(root), word);
  } else if (command === USER && word) {
    files.append(userFile, word);
  } else {
    return null;
  }
  for (const held of documents.keys()) publish(held);
  return null;
});

connection.onShutdown(() => {
  pending.clear();
  documents.clear();
  overlooked.clear();
});

connection.listen();
