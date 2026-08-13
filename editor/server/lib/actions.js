const { suggest } = require("../../../src/qslex/web/core.js");

const QUICKFIX = "quickfix";
const OCCURRENCE = "quikscript.ignore.occurrence";
const PROJECT = "quikscript.ignore.project";
const USER = "quikscript.ignore.user";
const COMMANDS = [OCCURRENCE, PROJECT, USER];
const HOARD = 4096;

/** @typedef {import("./check.js").Span} Span */
/** @typedef {{range: Span, newText: string}} Edit */
/** @typedef {{title: string, command: string, arguments: unknown[]}} Order */
/** @typedef {{title: string, kind: "quickfix", isPreferred?: boolean, edit?: {changes: Record<string, Edit[]>}, command?: Order}} Action */
/** @typedef {{word: string, occurrence: number, range: Span}} Flag */

/**
 * @param {import("./lexicon.js").Lexicon} held
 * @returns {(word: string) => string[]}
 */
function adviser(held) {
  /** @type {Map<string, string[]>} */
  const cached = new Map();
  const advice = {
    active: held.active,
    freq: held.counts,
    groups: held.groups,
    letters: held.letters,
    rep: held.rep,
  };
  return (word) => {
    let offers = cached.get(word);
    if (offers === undefined) {
      if (cached.size >= HOARD) cached.clear();
      offers = suggest(word, advice);
      cached.set(word, offers);
    }
    return offers;
  };
}

/**
 * @param {string} title
 * @param {string} command
 * @param {unknown[]} args
 * @returns {Action}
 */
function told(title, command, args) {
  return { title, kind: QUICKFIX, command: { title, command, arguments: args } };
}

/**
 * @param {string} uri
 * @param {Flag} flag
 * @param {Span[]} everywhere
 * @param {string[]} offers
 * @param {boolean} project
 * @returns {Action[]}
 */
function actions(uri, flag, everywhere, offers, project) {
  /** @type {Action[]} */
  const out = [];
  const others = everywhere.length - 1;
  const rest = others === 1 ? "the 1 other" : `the ${others} others`;
  for (const [at, fix] of offers.entries()) {
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
    told("Ignore this occurrence", OCCURRENCE, [
      { uri, word: flag.word, occurrence: flag.occurrence },
    ]),
  );
  if (project) out.push(told("Ignore in this project", PROJECT, [{ uri, word: flag.word }]));
  out.push(told("Ignore everywhere", USER, [{ word: flag.word }]));
  return out;
}

module.exports = { COMMANDS, OCCURRENCE, PROJECT, USER, actions, adviser };
