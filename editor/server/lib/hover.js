const { tokens } = require("../../../src/qslex/web/core.js");
const { COLUMN_LABEL, CONTRACTION, JUNIOR, SENIOR, X, label, spellingIn } = require("./lookup.js");

const HYPHEN = "-";
const SPACE = " ";
const GAP = "  ";
const FENCE = "```";
const TAG = "plaintext";
/** @type {Record<string, string>} */
const GLOSS_COLUMN_LABEL = { ...COLUMN_LABEL, [CONTRACTION]: "Senior contraction" };

/** @typedef {import("./lookup.js").Reading} Reading */
/** @typedef {import("./lookup.js").Writing} Writing */

/**
 * @param {string[]} lines
 * @returns {string}
 */
function fenced(lines) {
  return [FENCE + TAG, ...lines, FENCE].join("\n");
}

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
      if (spellingIn(row, entry.column) !== word) continue;
      let siblings = columns.get(entry.column);
      if (!siblings) {
        siblings = new Map();
        columns.set(entry.column, siblings);
      }
      for (const other of [SENIOR, JUNIOR, X]) {
        const form = spellingIn(row, other);
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
    lines.push(`${COLUMN_LABEL[column]} form:`);
    lines.push(
      fenced(
        [...siblings].map(
          (pair) => `${COLUMN_LABEL[pair[0]]}: ${[...pair[1]].sort().join(", ")}`,
        ),
      ),
    );
  }
  if (entries.some((entry) => entry.column === CONTRACTION)) {
    const forms = [...written].sort();
    if (forms.length > 0) {
      lines.push("Senior contraction — written out:");
      lines.push(fenced(forms));
    } else {
      lines.push("Senior contraction");
    }
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
    const group = grouped.get(entry.latin);
    if (group) group.push(entry);
    else grouped.set(entry.latin, [entry]);
  }
  const latinSections = [...grouped].map((pair) => section(word, pair[0], pair[1], write));
  return [fenced([word]), ...latinSections].join("\n\n");
}

/**
 * @param {string} word
 * @param {Map<string, Reading[]>} read
 * @param {Map<string, Writing[]>} write
 * @returns {string | null}
 */
function hoverMarkdown(word, read, write) {
  const entries = read.get(word);
  if (entries) return sections(word, entries, write);
  if (!word.includes(HYPHEN)) return null;
  /** @type {string[]} */
  const found = [];
  for (const piece of word.split(HYPHEN)) {
    const matches = read.get(piece);
    if (matches) found.push(sections(piece, matches, write));
  }
  return found.length > 0 ? found.join("\n\n") : null;
}

/**
 * @param {Reading[]} entries
 * @returns {string}
 */
function named(entries) {
  /** @type {Map<string, Reading[]>} */
  const grouped = new Map();
  for (const entry of entries) {
    const group = grouped.get(entry.latin);
    if (group) group.push(entry);
    else grouped.set(entry.latin, [entry]);
  }
  /** @type {string[]} */
  const glosses = [];
  for (const [latin, group] of grouped) {
    /** @type {string[]} */
    const labels = [];
    /** @type {string[]} */
    const columnLabels = [];
    for (const entry of group) {
      const tag = label(entry.pos);
      if (!labels.includes(tag)) labels.push(tag);
      if (entry.column === SENIOR) continue;
      const columnLabel = GLOSS_COLUMN_LABEL[entry.column];
      if (columnLabel && !columnLabels.includes(columnLabel)) columnLabels.push(columnLabel);
    }
    const noSeniorEntry = group.every((entry) => entry.column !== SENIOR);
    const columnSuffix =
      noSeniorEntry && columnLabels.length > 0 ? ` (${columnLabels.join(", ")})` : "";
    glosses.push(`${latin} — ${labels.join(", ")}${columnSuffix}`);
  }
  return glosses.join("; ");
}

/**
 * @param {string} word
 * @param {Map<string, Reading[]>} read
 * @returns {string | null}
 */
function latinWordsFor(word, read) {
  const entries = read.get(word);
  if (!entries) return null;
  /** @type {string[]} */
  const out = [];
  for (const entry of entries) {
    if (!out.includes(entry.latin)) out.push(entry.latin);
  }
  return out.join("/");
}

/**
 * @param {string} word
 * @param {Map<string, Reading[]>} read
 * @returns {string}
 */
function glossFromPieces(word, read) {
  /** @type {string[]} */
  const parts = [];
  for (const part of word.split(SPACE)) {
    /** @type {string[]} */
    const cut = [];
    for (const piece of part.split(HYPHEN)) {
      const latinWords = latinWordsFor(piece, read);
      if (latinWords) cut.push(latinWords);
    }
    if (cut.length > 0) parts.push(cut.join(HYPHEN));
  }
  return parts.join(SPACE);
}

/**
 * @param {string} word
 * @param {Map<string, Reading[]>} read
 * @returns {string}
 */
function glossed(word, read) {
  const entries = read.get(word);
  return entries ? named(entries) : glossFromPieces(word, read);
}

/**
 * @param {string[]} suggestions
 * @param {Map<string, Reading[]>} read
 * @returns {string[]}
 */
function listed(suggestions, read) {
  return suggestions.map((fix) => {
    const gloss = glossed(fix, read);
    return gloss ? `${fix}${GAP}${gloss}` : fix;
  });
}

/**
 * @param {string} text
 * @param {number} offset
 * @param {Map<string, Reading[]>} read
 * @param {Map<string, Writing[]>} write
 * @returns {{value: string, start: number, end: number} | null}
 */
function hoverAt(text, offset, read, write) {
  let token = null;
  for (const hit of tokens(text)) {
    if (hit.start > offset) break;
    if (offset < hit.end) {
      token = hit;
      break;
    }
    if (offset === hit.end) token = hit;
  }
  if (!token) return null;
  const value = hoverMarkdown(token.word, read, write);
  return value ? { value, start: token.start, end: token.end } : null;
}

module.exports = { glossed, hoverAt, hoverMarkdown, listed };
