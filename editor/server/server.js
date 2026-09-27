const path = require("node:path");
const { fileURLToPath } = require("node:url");
const {
  CompletionItemKind,
  CompletionTriggerKind,
  createConnection,
  TextDocumentSyncKind,
} = require("vscode-languageserver/node");
const data = require("./payload.json");
const { tokens } = require("../../src/qslex/web/core.js");
const { lexicon } = require("./lib/lexicon.js");
const {
  MAX_DIAGNOSTICS,
  diagnostics,
  flagged,
  lineStarts,
  occurrenceKey,
  offsetAt,
  position,
} = require("./lib/check.js");
const { debouncer } = require("./lib/debounce.js");
const {
  COMMANDS,
  DIRECTORY,
  OCCURRENCE,
  PROJECT,
  USER,
  actions,
  cachedSuggester,
} = require("./lib/actions.js");
const {
  ancestorIgnorePaths,
  ignoreFileCache,
  projectIgnorePath,
  userIgnorePath,
} = require("./lib/ignores.js");
const { skipRanges } = require("./lib/markdown.js");
const { parseLatinBySpelling, parseSpellingsByLatin } = require("./lib/lookup.js");
const { glossed, hoverAt, listed } = require("./lib/hover.js");
const { completions, lookupSpellings } = require("./lib/complete.js");

const DELAY = 200;
const MAX_ACTION_WORK = 10000;
const TIME_LIMIT_MS = 500;
const MODES = ["off", "onDemand", "auto"];
const MARKDOWN = "markdown";
const MAX_LOOKUP_TEXT = 200;

/** @typedef {import("./lib/check.js").Span} Span */
/** @typedef {import("./lib/actions.js").Edit} Edit */
/** @typedef {{command: string, arguments: unknown[]}} Order */
/** @typedef {{fix: string, gloss: string, edit: {changes: Record<string, Edit[]>}}} Suggestion */
/** @typedef {{word: string, occurrence: number, range: Span, spans: Span[], fixes: Suggestion[], ignore: {occurrence: Order, directory: Order | null, project: Order | null, user: Order}}} Fixed */

const connection = createConnection();
const words = lexicon(data);
const suggestionsFor = cachedSuggester(words);
const files = ignoreFileCache();
const userFile = userIgnorePath(process.env);
/** @type {Map<string, {text: string, languageId: string, version: number}>} */
const documents = new Map();
/** @type {Map<string, Set<string>>} */
const ignoredOccurrences = new Map();
/** @type {string[]} */
let roots = [];
let inlineCodeActions = false;
let completionMode = MODES[0];
let canPullConfiguration = false;
/** @type {Map<string, import("./lib/lookup.js").LatinEntry[]> | null} */
let latinBySpelling = null;
/** @type {Map<string, import("./lib/lookup.js").SpellingEntry[]> | null} */
let spellingsByLatin = null;
const pending = debouncer(DELAY, publish);

function getLatinBySpelling() {
  if (!latinBySpelling) latinBySpelling = parseLatinBySpelling(data);
  return latinBySpelling;
}

function getSpellingsByLatin() {
  if (!spellingsByLatin) spellingsByLatin = parseSpellingsByLatin(data);
  return spellingsByLatin;
}

/**
 * @param {unknown} value
 * @param {string} fallback
 * @returns {string}
 */
function parseCompletionMode(value, fallback) {
  return typeof value === "string" && MODES.includes(value) ? value : fallback;
}

function pullConfiguration() {
  connection.workspace
    .getConfiguration({ section: "quikscript" })
    .then((settings) => {
      completionMode = parseCompletionMode(settings?.completions, completionMode);
    })
    .catch(() => {});
}

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
function directoryOf(uri) {
  const file = localPath(uri);
  return file ? path.dirname(file) : null;
}

/** @param {string} uri */
function ignoreScopesFor(uri) {
  const root = projectRoot(uri);
  const home = directoryOf(uri);
  return { directory: home !== null && home !== root, project: root !== null };
}

/** @param {string} uri */
function ignoredWordsFor(uri) {
  const file = localPath(uri);
  const home = file ? path.dirname(file) : roots[0];
  const sources = home ? ancestorIgnorePaths(home) : [];
  return files.read([...sources, userFile]);
}

/** @param {string} uri */
function ignoredOccurrencesFor(uri) {
  let keys = ignoredOccurrences.get(uri);
  if (!keys) {
    keys = new Set();
    ignoredOccurrences.set(uri, keys);
  }
  return keys;
}

/** @param {string} word */
function isSingleToken(word) {
  const runs = tokens(word);
  return runs.length === 1 && runs[0].start === 0 && runs[0].end === word.length;
}

/** @param {string} uri */
function checkDocument(uri) {
  const doc = documents.get(uri);
  if (!doc) return null;
  const hits = flagged(
    doc.text,
    doc.languageId,
    words.active,
    ignoredWordsFor(uri),
    ignoredOccurrencesFor(uri),
  );
  const found = diagnostics(doc.text, hits);
  const flags = hits.map((hit, at) => ({
    word: hit.word,
    occurrence: hit.occurrence,
    range: found[at].range,
  }));
  return { doc, found, flags };
}

/**
 * @param {import("./lib/actions.js").Flag[]} flags
 * @returns {Map<string, import("./lib/check.js").Span[]>}
 */
function rangesByWord(flags) {
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
function buildCodeActions(uri, flags, everywhere) {
  const scopes = ignoreScopesFor(uri);
  const started = Date.now();
  /** @type {import("./lib/actions.js").Action[][]} */
  const out = [];
  let work = 0;
  for (const flag of flags) {
    if (work >= MAX_ACTION_WORK || Date.now() - started >= TIME_LIMIT_MS) break;
    const built = actions(
      uri,
      flag,
      everywhere.get(flag.word) || [],
      suggestionsFor(flag.word),
      scopes,
    );
    out.push(built);
    for (const action of built) {
      work += 1 + (action.edit ? action.edit.changes[uri].length : 0);
    }
  }
  return out;
}

/**
 * @param {string} uri
 * @param {import("./lib/actions.js").Flag[]} flags
 * @param {Map<string, Span[]>} everywhere
 * @returns {Fixed[]}
 */
function buildFixList(uri, flags, everywhere) {
  const scopes = ignoreScopesFor(uri);
  const started = Date.now();
  /** @type {Fixed[]} */
  const out = [];
  let work = 0;
  for (const flag of flags) {
    if (work >= MAX_ACTION_WORK || Date.now() - started >= TIME_LIMIT_MS) break;
    const fixes = suggestionsFor(flag.word).map((fix) => ({
      fix,
      gloss: glossed(fix, getLatinBySpelling()),
      edit: { changes: { [uri]: [{ range: flag.range, newText: fix }] } },
    }));
    out.push({
      word: flag.word,
      occurrence: flag.occurrence,
      range: flag.range,
      spans: everywhere.get(flag.word) || [],
      fixes,
      ignore: {
        occurrence: {
          command: OCCURRENCE,
          arguments: [{ uri, word: flag.word, occurrence: flag.occurrence }],
        },
        directory: scopes.directory
          ? { command: DIRECTORY, arguments: [{ uri, word: flag.word }] }
          : null,
        project: scopes.project
          ? { command: PROJECT, arguments: [{ uri, word: flag.word }] }
          : null,
        user: { command: USER, arguments: [{ word: flag.word }] },
      },
    });
    work += 1 + fixes.length;
  }
  return out;
}

/**
 * @param {import("./lib/check.js").Diagnostic[]} found
 * @param {import("./lib/actions.js").Flag[]} flags
 * @returns {number}
 */
function appendSuggestionsToMessages(found, flags) {
  const started = Date.now();
  let lookedUpCount = 0;
  for (const [at, flag] of flags.entries()) {
    if (Date.now() - started >= TIME_LIMIT_MS) break;
    const lines = listed(suggestionsFor(flag.word), getLatinBySpelling());
    if (lines.length > 0) found[at].message = [found[at].message, ...lines].join("\n");
    lookedUpCount += 1;
  }
  return lookedUpCount;
}

/** @param {string} uri */
function publish(uri) {
  const result = checkDocument(uri);
  if (!result) return;
  const { doc, found, flags } = result;
  if (flags.length >= MAX_DIAGNOSTICS) {
    connection.console.log(`quikscript-lsp: diagnostics capped at ${MAX_DIAGNOSTICS} for ${uri}`);
  }
  const lookedUpCount = appendSuggestionsToMessages(found, flags);
  if (lookedUpCount < flags.length) {
    connection.console.log(
      `quikscript-lsp: suggestions looked up for ${lookedUpCount} of ${flags.length} messages before the time limit for ${uri}`,
    );
  }
  if (inlineCodeActions) {
    const lists = buildCodeActions(uri, flags, rangesByWord(flags));
    for (const [at, built] of lists.entries()) found[at].codeActions = built;
    if (lists.length < flags.length) {
      connection.console.log(`quikscript-lsp: inline code actions truncated for ${uri}`);
    }
  }
  connection
    .sendDiagnostics({ uri, version: doc.version, diagnostics: found })
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
  roots = folders.map((folder) => localPath(folder.uri)).filter((root) => root !== null);
  if (roots.length === 0 && params.rootUri) {
    const root = localPath(params.rootUri);
    if (root) roots = [root];
  }
  roots.sort((one, other) => other.length - one.length);
  const published = /** @type {any} */ (params.capabilities.textDocument?.publishDiagnostics);
  inlineCodeActions = Boolean(published && published.codeActionsInline);
  const options = /** @type {{completions?: unknown} | undefined} */ (
    params.initializationOptions
  );
  completionMode = parseCompletionMode(options?.completions, completionMode);
  canPullConfiguration = Boolean(params.capabilities.workspace?.configuration);
  return {
    capabilities: {
      textDocumentSync: { openClose: true, change: TextDocumentSyncKind.Full },
      codeActionProvider: { codeActionKinds: ["quickfix"] },
      executeCommandProvider: { commands: COMMANDS },
      hoverProvider: true,
      completionProvider: {},
    },
    serverInfo: { name: "quikscript-lsp" },
  };
});

connection.onInitialized(() => {
  connection.console.log(`quikscript-lsp: ${words.active.size} spellings loaded`);
  if (canPullConfiguration) pullConfiguration();
});

connection.onDidChangeConfiguration((change) => {
  if (canPullConfiguration) {
    pullConfiguration();
    return;
  }
  const pushed = /** @type {{quikscript?: {completions?: unknown}} | undefined} */ (
    change.settings
  );
  completionMode = parseCompletionMode(pushed?.quikscript?.completions, completionMode);
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
  const doc = documents.get(textDocument.uri);
  if (!doc) return;
  let whole = false;
  for (const change of contentChanges) {
    if ("range" in change) continue;
    doc.text = change.text;
    whole = true;
  }
  if (!whole) {
    if (!warned) {
      warned = true;
      connection.console.warn(
        "quikscript-lsp: ignoring ranged changes; this server supports only full-document sync",
      );
    }
    return;
  }
  doc.version = textDocument.version;
  pending.schedule(textDocument.uri);
});

connection.onDidCloseTextDocument(({ textDocument }) => {
  pending.cancel(textDocument.uri);
  documents.delete(textDocument.uri);
  ignoredOccurrences.delete(textDocument.uri);
  connection
    .sendDiagnostics({ uri: textDocument.uri, diagnostics: [] })
    .catch(() => {});
});

connection.onHover(({ textDocument, position: place }) => {
  const doc = documents.get(textDocument.uri);
  if (!doc) return null;
  const starts = lineStarts(doc.text);
  const found = hoverAt(
    doc.text,
    offsetAt(starts, doc.text, place),
    getLatinBySpelling(),
    getSpellingsByLatin(),
  );
  if (!found) return null;
  return {
    contents: { kind: "markdown", value: found.value },
    range: { start: position(starts, found.start), end: position(starts, found.end) },
  };
});

connection.onCompletion(({ textDocument, position: place, context }) => {
  if (completionMode === "off") return null;
  if (
    completionMode === "onDemand" &&
    context &&
    context.triggerKind !== CompletionTriggerKind.Invoked
  ) {
    return null;
  }
  const doc = documents.get(textDocument.uri);
  if (!doc) return null;
  const starts = lineStarts(doc.text);
  const found = completions(doc.text, offsetAt(starts, doc.text, place), getSpellingsByLatin());
  if (!found) return null;
  if (doc.languageId.toLowerCase() === MARKDOWN) {
    for (const span of skipRanges(doc.text)) {
      if (span.start >= found.end) break;
      if (found.start < span.end) return null;
    }
  }
  const range = {
    start: position(starts, found.start),
    end: position(starts, found.end),
  };
  return found.items.map((item) => ({
    ...item,
    kind: CompletionItemKind.Text,
    filterText: found.word,
    textEdit: { range, newText: item.label },
  }));
});

connection.onCodeAction(({ textDocument, range, context }) => {
  const only = context.only;
  if (only && !only.some((kind) => kind === "quickfix" || "quickfix".startsWith(kind + "."))) {
    return null;
  }
  const result = checkDocument(textDocument.uri);
  if (!result) return null;
  const { flags } = result;
  const chosen = flags.filter((flag) => touches(flag.range, range));
  return buildCodeActions(textDocument.uri, chosen, rangesByWord(flags)).flat();
});

connection.onRequest(
  "quikscript/fixes",
  (/** @type {{textDocument: {uri: string}}} */ { textDocument }) => {
    const result = checkDocument(textDocument.uri);
    if (!result) return { flags: [] };
    const { flags } = result;
    const built = buildFixList(textDocument.uri, flags, rangesByWord(flags));
    if (built.length < flags.length) {
      connection.console.log(`quikscript-lsp: fix list truncated for ${textDocument.uri}`);
    }
    return { flags: built };
  },
);

connection.onRequest("quikscript/spellings", (/** @type {{text?: unknown}} */ asked) => {
  const text = typeof asked?.text === "string" ? asked.text.slice(0, MAX_LOOKUP_TEXT) : "";
  return { words: lookupSpellings(text, getSpellingsByLatin()) };
});

connection.onExecuteCommand(({ command, arguments: args }) => {
  const asked = /** @type {{uri?: unknown, word?: unknown, occurrence?: unknown}} */ (
    (args && args[0]) || {}
  );
  const uri = typeof asked.uri === "string" && documents.has(asked.uri) ? asked.uri : null;
  const word = typeof asked.word === "string" && isSingleToken(asked.word) ? asked.word : null;
  const count =
    typeof asked.occurrence === "number" &&
    Number.isInteger(asked.occurrence) &&
    asked.occurrence >= 0
      ? asked.occurrence
      : null;
  if (command === OCCURRENCE && uri && word && count !== null) {
    ignoredOccurrencesFor(uri).add(occurrenceKey(word, count));
  } else if (command === DIRECTORY && uri && word) {
    const home = directoryOf(uri);
    if (!home) return null;
    files.append(projectIgnorePath(home), word);
  } else if (command === PROJECT && uri && word) {
    const root = projectRoot(uri);
    if (!root) return null;
    files.append(projectIgnorePath(root), word);
  } else if (command === USER && word) {
    files.append(userFile, word);
  } else {
    return null;
  }
  for (const documentUri of documents.keys()) publish(documentUri);
  return null;
});

connection.onShutdown(() => {
  pending.clear();
  documents.clear();
  ignoredOccurrences.clear();
});

connection.listen();
