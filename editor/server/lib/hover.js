const { tokens } = require("../../../src/qslex/web/core.js");
const { CONTRACTION, FACE_OF, JUNIOR, SENIOR, X, faced, label } = require("./lookup.js");

const HYPHEN = "-";
const SPACE = " ";
const GAP = "  ";
const FENCE = "```";
const TAG = "plaintext";
const UNKNOWN = "Unknown Quikscript spelling.";
const NONE = "No suggestions.";
/** @type {Record<string, string>} */
const NAMED_FACE = { ...FACE_OF, [CONTRACTION]: "Senior contraction" };

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
    lines.push(`${FACE_OF[column]} form:`);
    lines.push(
      fenced(
        [...siblings].map((pair) => `${FACE_OF[pair[0]]}: ${[...pair[1]].sort().join(", ")}`),
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
    const held = grouped.get(entry.latin);
    if (held) held.push(entry);
    else grouped.set(entry.latin, [entry]);
  }
  const told = [...grouped].map((pair) => section(word, pair[0], pair[1], write));
  return [fenced([word]), ...told].join("\n\n");
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
 * @param {Reading[]} entries
 * @returns {string}
 */
function named(entries) {
  /** @type {Map<string, Reading[]>} */
  const grouped = new Map();
  for (const entry of entries) {
    const held = grouped.get(entry.latin);
    if (held) held.push(entry);
    else grouped.set(entry.latin, [entry]);
  }
  /** @type {string[]} */
  const told = [];
  for (const [latin, held] of grouped) {
    /** @type {string[]} */
    const labels = [];
    /** @type {string[]} */
    const faces = [];
    for (const entry of held) {
      const tag = label(entry.pos);
      if (!labels.includes(tag)) labels.push(tag);
      if (entry.column === SENIOR) continue;
      const face = NAMED_FACE[entry.column];
      if (face && !faces.includes(face)) faces.push(face);
    }
    const apart = held.every((entry) => entry.column !== SENIOR);
    const aside = apart && faces.length > 0 ? ` (${faces.join(", ")})` : "";
    told.push(`${latin} — ${labels.join(", ")}${aside}`);
  }
  return told.join("; ");
}

/**
 * @param {string} word
 * @param {Map<string, Reading[]>} read
 * @returns {string | null}
 */
function latins(word, read) {
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
function pieced(word, read) {
  /** @type {string[]} */
  const parts = [];
  for (const part of word.split(SPACE)) {
    /** @type {string[]} */
    const cut = [];
    for (const piece of part.split(HYPHEN)) {
      const held = latins(piece, read);
      if (held) cut.push(held);
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
  return entries ? named(entries) : pieced(word, read);
}

/**
 * @param {string[]} offers
 * @param {Map<string, Reading[]>} read
 * @returns {string}
 */
function advised(offers, read) {
  if (offers.length === 0) return `${UNKNOWN} ${NONE}`;
  const lines = offers.map((fix) => {
    const gloss = glossed(fix, read);
    return gloss ? `${fix}${GAP}${gloss}` : fix;
  });
  return [UNKNOWN, fenced(lines)].join("\n\n");
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

module.exports = { advised, described, glossed, hovered };
