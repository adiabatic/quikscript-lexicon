const { suggest } = require("../../../src/qslex/web/core.js");

const QUICKFIX = "quickfix";
const OCCURRENCE = "quikscript.ignore.occurrence";
const DIRECTORY = "quikscript.ignore.directory";
const PROJECT = "quikscript.ignore.project";
const USER = "quikscript.ignore.user";
const COMMANDS = [OCCURRENCE, DIRECTORY, PROJECT, USER];
const SUGGESTION_CACHE_LIMIT = 4096;

/** @typedef {import("./check.js").Span} Span */
/** @typedef {{range: Span, newText: string}} Edit */
/** @typedef {{title: string, command: string, arguments: unknown[]}} Order */
/** @typedef {{title: string, kind: "quickfix", isPreferred?: boolean, edit?: {changes: Record<string, Edit[]>}, command?: Order}} Action */
/** @typedef {{word: string, occurrence: number, range: Span}} Flag */

/**
 * @param {import("./lexicon.js").Lexicon} lexicon
 * @returns {(word: string) => string[]}
 */
function cachedSuggester(lexicon) {
  /** @type {Map<string, string[]>} */
  const cached = new Map();
  const suggestContext = {
    active: lexicon.active,
    freq: lexicon.counts,
    groups: lexicon.groups,
    letters: lexicon.letters,
    rep: lexicon.rep,
  };
  return (word) => {
    let suggestions = cached.get(word);
    if (suggestions === undefined) {
      if (cached.size >= SUGGESTION_CACHE_LIMIT) cached.clear();
      suggestions = suggest(word, suggestContext);
      cached.set(word, suggestions);
    }
    return suggestions;
  };
}

/**
 * @param {string} title
 * @param {string} command
 * @param {unknown[]} args
 * @returns {Action}
 */
function commandAction(title, command, args) {
  return { title, kind: QUICKFIX, command: { title, command, arguments: args } };
}

/**
 * @param {string} uri
 * @param {Flag} flag
 * @param {Span[]} everywhere
 * @param {string[]} suggestions
 * @param {{directory: boolean, project: boolean}} scopes
 * @returns {Action[]}
 */
function actions(uri, flag, everywhere, suggestions, scopes) {
  /** @type {Action[]} */
  const out = [];
  const others = everywhere.length - 1;
  const rest = others === 1 ? "the 1 other" : `the ${others} others`;
  for (const [at, fix] of suggestions.entries()) {
    /** @type {Action} */
    const one = {
      title: fix,
      kind: QUICKFIX,
      edit: { changes: { [uri]: [{ range: flag.range, newText: fix }] } },
    };
    if (at === 0) one.isPreferred = true;
    out.push(one);
    if (others > 0) {
      out.push({
        title: `${fix} — and ${rest} written the same way`,
        kind: QUICKFIX,
        edit: {
          changes: { [uri]: everywhere.map((span) => ({ range: span, newText: fix })) },
        },
      });
    }
  }
  out.push(
    commandAction("Ignore this occurrence", OCCURRENCE, [
      { uri, word: flag.word, occurrence: flag.occurrence },
    ]),
  );
  if (scopes.directory) {
    out.push(commandAction("Ignore in this directory", DIRECTORY, [{ uri, word: flag.word }]));
  }
  if (scopes.project) {
    out.push(commandAction("Ignore in this project", PROJECT, [{ uri, word: flag.word }]));
  }
  out.push(commandAction("Ignore everywhere", USER, [{ word: flag.word }]));
  return out;
}

module.exports = { COMMANDS, DIRECTORY, OCCURRENCE, PROJECT, USER, actions, cachedSuggester };
