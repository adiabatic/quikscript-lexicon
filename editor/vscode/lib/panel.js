/** @typedef {{line: number, character: number}} Position */
/** @typedef {{start: Position, end: Position}} Span */
/** @typedef {{range: Span, newText: string}} Edit */
/** @typedef {{changes: Record<string, Edit[]>}} Change */
/** @typedef {{command: string, arguments: unknown[]}} Command */
/** @typedef {{fix: string, gloss: string, edit: Change}} Suggestion */
/** @typedef {"occurrence" | "directory" | "project" | "user"} IgnoreScope */
/** @typedef {{occurrence: Command, directory: Command | null, project: Command | null, user: Command}} Ignore */
/** @typedef {{word: string, occurrence: number, range: Span, spans: Span[], fixes: Suggestion[], ignore: Ignore}} Flag */
/** @typedef {{uri: string, flags: Flag[]}} DocumentFlags */
/** @typedef {{kind: "word", flag: number, word: string, occurrence: number, others: number, line: number, character: number}} WordRow */
/** @typedef {{kind: "none"}} NoSuggestionsRow */
/** @typedef {{kind: "suggestion", flag: number, at: number, fix: string, gloss: string, others: number}} SuggestionRow */
/** @typedef {{kind: "ignore", flag: number, scope: IgnoreScope, label: string}} IgnoreRow */
/** @typedef {WordRow | NoSuggestionsRow | SuggestionRow | IgnoreRow} Row */
/** @typedef {{type: "fix", flag: number, at: number, all: boolean}} FixMessage */
/** @typedef {{type: "ignore", flag: number, scope: IgnoreScope}} IgnoreMessage */
/** @typedef {{type: "reveal", flag: number}} RevealMessage */
/** @typedef {{type: "typed", flag: number, fix: string, all: boolean}} TypedFixMessage */
/** @typedef {FixMessage | IgnoreMessage | RevealMessage | TypedFixMessage} Message */
/** @typedef {{edit: Change} | {command: Command} | {range: Span} | null} Resolution */
/** @typedef {{rows: Row[], note: string}} State */
/** @typedef {{label: string, detail: string}} LookupItem */
/** @typedef {{latin: string, items: LookupItem[]}} LookupResult */
/** @typedef {{kind: "phrase", fix: string}} PhraseRow */
/** @typedef {{kind: "form", fix: string, gloss: string}} FormRow */
/** @typedef {{kind: "missing", latin: string}} MissingRow */
/** @typedef {PhraseRow | FormRow | MissingRow} LookupRow */

/** @type {[IgnoreScope, string][]} */
const IGNORE_SCOPES = [
  ["occurrence", "Ignore this occurrence"],
  ["directory", "Ignore in this directory"],
  ["project", "Ignore in this project"],
  ["user", "Ignore everywhere"],
];

/**
 * @param {Flag[]} flags
 * @returns {Row[]}
 */
function rows(flags) {
  /** @type {Row[]} */
  const out = [];
  for (const [index, flag] of flags.entries()) {
    const { line, character } = flag.range.start;
    const others = flag.spans.length - 1;
    const { word, occurrence } = flag;
    out.push({ kind: "word", flag: index, word, occurrence, others, line, character });
    if (flag.fixes.length === 0) out.push({ kind: "none" });
    for (const [at, { fix, gloss }] of flag.fixes.entries()) {
      out.push({ kind: "suggestion", flag: index, at, fix, gloss, others });
    }
    for (const [scope, label] of IGNORE_SCOPES) {
      if (flag.ignore[scope]) out.push({ kind: "ignore", flag: index, scope, label });
    }
  }
  return out;
}

/**
 * @param {DocumentFlags} documentFlags
 * @param {Flag} flag
 * @param {string} fix
 * @param {boolean} all
 * @returns {Resolution}
 */
function fixEdit(documentFlags, flag, fix, all) {
  const spans = all ? flag.spans : [flag.range];
  const changes = spans.map((range) => ({ range, newText: fix }));
  return { edit: { changes: { [documentFlags.uri]: changes } } };
}

/**
 * @param {DocumentFlags} documentFlags
 * @param {Message} message
 * @returns {Resolution}
 */
function resolveMessage(documentFlags, message) {
  const flag = documentFlags.flags[message.flag];
  if (!flag) return null;
  if (message.type === "reveal") return { range: flag.range };
  if (message.type === "ignore") {
    const command = flag.ignore[message.scope];
    return command ? { command } : null;
  }
  if (message.type === "typed") {
    return message.fix ? fixEdit(documentFlags, flag, message.fix, message.all) : null;
  }
  const suggestion = flag.fixes[message.at];
  if (!suggestion) return null;
  if (!message.all) return { edit: suggestion.edit };
  return fixEdit(documentFlags, flag, suggestion.fix, true);
}

/**
 * @param {LookupResult[]} words
 * @returns {LookupRow[]}
 */
function lookupRows(words) {
  /** @type {LookupRow[]} */
  const out = [];
  if (words.length > 1 && words.every((word) => word.items.length > 0)) {
    out.push({ kind: "phrase", fix: words.map((word) => word.items[0].label).join(" ") });
  }
  for (const word of words) {
    if (word.items.length === 0) {
      out.push({ kind: "missing", latin: word.latin });
      continue;
    }
    for (const item of word.items) {
      const gloss = words.length > 1 ? `${word.latin} — ${item.detail}` : item.detail;
      out.push({ kind: "form", fix: item.label, gloss });
    }
  }
  return out;
}

/**
 * @param {{csp: string, styles: string[], script: string}} parts
 * @returns {string}
 */
function shell({ csp, styles, script }) {
  const policy = `default-src 'none'; font-src ${csp} data:; style-src ${csp}; script-src ${csp};`;
  return [
    "<!doctype html>",
    '<html lang="en">',
    "<head>",
    '<meta charset="utf-8">',
    `<meta http-equiv="Content-Security-Policy" content="${policy}">`,
    ...styles.map((href) => `<link rel="stylesheet" href="${href}">`),
    "</head>",
    "<body>",
    "<main></main>",
    `<script src="${script}"></script>`,
    "</body>",
    "</html>",
  ].join("\n");
}

module.exports = { lookupRows, resolveMessage, rows, shell };
