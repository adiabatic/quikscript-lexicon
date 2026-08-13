const { tokens } = require("../../../src/qslex/web/core.js");
const { CONTRACTION, FACE_OF, JUNIOR, SENIOR, X, faced, label } = require("./lookup.js");

const HYPHEN = "-";

/** @typedef {import("./lookup.js").Reading} Reading */
/** @typedef {import("./lookup.js").Writing} Writing */

/**
 * @param {string} word
 * @param {string} latin
 * @param {Reading[]} entries
 * @param {Map<string, Writing[]>} write
 * @returns {string}
 */
function section(word, latin, entries, write) {
  /** @type {string[]} */
  const labels = [];
  for (const entry of entries) {
    const named = label(entry.pos);
    if (!labels.includes(named)) labels.push(named);
  }
  const rows = write.get(latin) || [];
  /** @type {Map<string, Map<string, Set<string>>>} */
  const columns = new Map();
  /** @type {Set<string>} */
  const written = new Set();
  for (const entry of entries) {
    for (const row of rows) {
      if (row.pos !== entry.pos) continue;
      if (entry.column === CONTRACTION) {
        if (row.senior && row.senior !== word) written.add(row.senior);
        continue;
      }
      if (faced(row, entry.column) !== word) continue;
      let siblings = columns.get(entry.column);
      if (!siblings) {
        siblings = new Map();
        columns.set(entry.column, siblings);
      }
      for (const other of [SENIOR, JUNIOR, X]) {
        const form = faced(row, other);
        if (other === entry.column || !form || form === word) continue;
        const forms = siblings.get(other);
        if (forms) forms.add(form);
        else siblings.set(other, new Set([form]));
      }
    }
  }
  const lines = [`**${latin}** — ${labels.join(", ")}`];
  for (const [column, siblings] of columns) {
    if (siblings.size === 0) continue;
    const parts = [...siblings].map(
      ([other, forms]) => `${FACE_OF[other]}: ${[...forms].sort().join(", ")}`,
    );
    lines.push(`${FACE_OF[column]} form — ${parts.join("; ")}`);
  }
  if (entries.some((entry) => entry.column === CONTRACTION)) {
    const forms = [...written].sort().join(", ");
    lines.push(
      forms ? `Senior contraction — written out ${forms}` : "Senior contraction",
    );
  }
  return lines.join("  \n");
}

/**
 * @param {string} word
 * @param {Reading[]} entries
 * @param {Map<string, Writing[]>} write
 * @returns {string}
 */
function sections(word, entries, write) {
  /** @type {Map<string, Reading[]>} */
  const grouped = new Map();
  for (const entry of entries) {
    const held = grouped.get(entry.latin);
    if (held) held.push(entry);
    else grouped.set(entry.latin, [entry]);
  }
  const told = [...grouped].map(([latin, held]) => section(word, latin, held, write));
  return [word, ...told].join("\n\n");
}

/**
 * @param {string} word
 * @param {Map<string, Reading[]>} read
 * @param {Map<string, Writing[]>} write
 * @returns {string | null}
 */
function described(word, read, write) {
  const entries = read.get(word);
  if (entries) return sections(word, entries, write);
  if (!word.includes(HYPHEN)) return null;
  /** @type {string[]} */
  const found = [];
  for (const piece of word.split(HYPHEN)) {
    const held = read.get(piece);
    if (held) found.push(sections(piece, held, write));
  }
  return found.length > 0 ? found.join("\n\n") : null;
}

/**
 * @param {string} text
 * @param {number} offset
 * @param {Map<string, Reading[]>} read
 * @param {Map<string, Writing[]>} write
 * @returns {{value: string, start: number, end: number} | null}
 */
function hovered(text, offset, read, write) {
  let behind = null;
  for (const hit of tokens(text)) {
    if (hit.start > offset) break;
    if (offset < hit.end) {
      behind = hit;
      break;
    }
    if (offset === hit.end) behind = hit;
  }
  if (!behind) return null;
  const value = described(behind.word, read, write);
  return value ? { value, start: behind.start, end: behind.end } : null;
}

module.exports = { described, hovered };
