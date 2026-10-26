const { tokens } = require("../../../src/qslex/web/core.js");
const { COLUMN_LABEL, CONTRACTION, JUNIOR, SENIOR, X, label, spellingIn } = require("./lookup.js");

const HYPHEN = "-";
const SPACE = " ";
const GAP = "  ";
const FENCE = "```";
const TAG = "plaintext";
/** @type {Record<string, string>} */
const GLOSS_COLUMN_LABEL = { ...COLUMN_LABEL, [CONTRACTION]: "Senior contraction" };

/** @typedef {import("./lookup.js").LatinEntry} LatinEntry */
/** @typedef {import("./lookup.js").SpellingEntry} SpellingEntry */

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
 * @param {LatinEntry[]} entries
 * @param {Map<string, SpellingEntry[]>} spellingsByLatin
 * @returns {string}
 */
function section(word, latin, entries, spellingsByLatin) {
  /** @type {string[]} */
  const labels = [];
  for (const entry of entries) {
    const posLabel = label(entry.pos);
    if (!labels.includes(posLabel)) labels.push(posLabel);
  }
  const rows = spellingsByLatin.get(latin) || [];
  /** @type {Map<string, Map<string, Set<string>>>} */
  const columns = new Map();
  /** @type {Set<string>} */
  const uncontractedForms = new Set();
  for (const entry of entries) {
    for (const row of rows) {
      if (row.pos !== entry.pos) continue;
      if (entry.column === CONTRACTION) {
        if (row.senior && row.senior !== word) uncontractedForms.add(row.senior);
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
    const forms = [...uncontractedForms].sort();
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
 * @param {LatinEntry[]} entries
 * @param {Map<string, SpellingEntry[]>} spellingsByLatin
 * @returns {string}
 */
function sections(word, entries, spellingsByLatin) {
  /** @type {Map<string, LatinEntry[]>} */
  const grouped = new Map();
  for (const entry of entries) {
    const group = grouped.get(entry.latin);
    if (group) group.push(entry);
    else grouped.set(entry.latin, [entry]);
  }
  const latinSections = [...grouped].map((pair) =>
    section(word, pair[0], pair[1], spellingsByLatin),
  );
  return [fenced([word]), ...latinSections].join("\n\n");
}

/**
 * @param {string} word
 * @param {Map<string, LatinEntry[]>} latinBySpelling
 * @param {Map<string, SpellingEntry[]>} spellingsByLatin
 * @returns {string | null}
 */
function hoverMarkdown(word, latinBySpelling, spellingsByLatin) {
  const entries = latinBySpelling.get(word);
  if (entries) return sections(word, entries, spellingsByLatin);
  if (!word.includes(HYPHEN)) return null;
  /** @type {string[]} */
  const found = [];
  for (const piece of word.split(HYPHEN)) {
    const matches = latinBySpelling.get(piece);
    if (matches) found.push(sections(piece, matches, spellingsByLatin));
  }
  return found.length > 0 ? found.join("\n\n") : null;
}

/**
 * @param {LatinEntry[]} entries
 * @returns {string}
 */
function glossForEntries(entries) {
  /** @type {Map<string, LatinEntry[]>} */
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
 * @param {Map<string, LatinEntry[]>} latinBySpelling
 * @returns {string | null}
 */
function latinWordsFor(word, latinBySpelling) {
  const entries = latinBySpelling.get(word);
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
 * @param {Map<string, LatinEntry[]>} latinBySpelling
 * @returns {string}
 */
function glossFromPieces(word, latinBySpelling) {
  /** @type {string[]} */
  const parts = [];
  for (const part of word.split(SPACE)) {
    /** @type {string[]} */
    const cut = [];
    for (const piece of part.split(HYPHEN)) {
      const latinWords = latinWordsFor(piece, latinBySpelling);
      if (latinWords) cut.push(latinWords);
    }
    if (cut.length > 0) parts.push(cut.join(HYPHEN));
  }
  return parts.join(SPACE);
}

/**
 * @param {string} word
 * @param {Map<string, LatinEntry[]>} latinBySpelling
 * @returns {string}
 */
function glossFor(word, latinBySpelling) {
  const entries = latinBySpelling.get(word);
  return entries ? glossForEntries(entries) : glossFromPieces(word, latinBySpelling);
}

/**
 * @param {string[]} suggestions
 * @param {Map<string, LatinEntry[]>} latinBySpelling
 * @returns {string[]}
 */
function suggestionLines(suggestions, latinBySpelling) {
  return suggestions.map((fix) => {
    const gloss = glossFor(fix, latinBySpelling);
    return gloss ? `${fix}${GAP}${gloss}` : fix;
  });
}

/**
 * @param {string} text
 * @param {number} offset
 * @param {Map<string, LatinEntry[]>} latinBySpelling
 * @param {Map<string, SpellingEntry[]>} spellingsByLatin
 * @returns {{value: string, start: number, end: number} | null}
 */
function hoverAt(text, offset, latinBySpelling, spellingsByLatin) {
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
  const value = hoverMarkdown(token.word, latinBySpelling, spellingsByLatin);
  return value ? { value, start: token.start, end: token.end } : null;
}

module.exports = { glossFor, hoverAt, hoverMarkdown, suggestionLines };
