const { COLUMN_LABEL, JUNIOR, SENIOR, X, label, spellingIn } = require("./lookup.js");

const LETTER = /[A-Za-z]/;
const WORDY = /[A-Za-z'’-]/;
const CURLY = /’/g;
const TRAILING = /'+$/;
const HYPHEN = "-";
const RUN = /[A-Za-z'’-]+/g;
const MAX_LOOKUP_WORDS = 20;

/** @typedef {import("./lookup.js").SpellingEntry} SpellingEntry */
/** @typedef {{label: string, detail: string, sortText: string}} Item */

/**
 * @param {string} text
 * @param {number} offset
 * @returns {{word: string, start: number, end: number} | null}
 */
function latinWordAt(text, offset) {
  let start = Math.min(Math.max(offset, 0), text.length);
  let end = start;
  while (start > 0 && WORDY.test(text[start - 1])) start -= 1;
  while (end < text.length && WORDY.test(text[end])) end += 1;
  if (start === end) return null;
  const word = text.slice(start, end);
  return LETTER.test(word) ? { word, start, end } : null;
}

/**
 * @param {SpellingEntry[]} senses
 * @returns {Item[]}
 */
function items(senses) {
  /** @type {Map<string, {labels: string[], frequency: number, columns: Set<string>}>} */
  const merged = new Map();
  for (const sense of senses) {
    for (const column of [SENIOR, JUNIOR, X]) {
      const form = spellingIn(sense, column);
      if (!form) continue;
      const named = label(sense.pos);
      const entry = merged.get(form);
      if (entry) {
        if (!entry.labels.includes(named)) entry.labels.push(named);
        entry.frequency = Math.max(entry.frequency, sense.frequency);
        entry.columns.add(column);
      } else {
        merged.set(form, {
          labels: [named],
          frequency: sense.frequency,
          columns: new Set([column]),
        });
      }
    }
  }
  const ranked = [...merged].sort(
    ([oneForm, one], [otherForm, other]) =>
      other.frequency - one.frequency ||
      Number(!one.columns.has(SENIOR)) - Number(!other.columns.has(SENIOR)) ||
      (oneForm < otherForm ? -1 : 1),
  );
  return ranked.map(([form, entry], at) => ({
    label: form,
    detail: entry.columns.has(SENIOR)
      ? entry.labels.join(", ")
      : `${entry.labels.join(", ")} — ${[...entry.columns]
          .map((column) => COLUMN_LABEL[column])
          .join(", ")} form`,
    sortText: String(at).padStart(4, "0"),
  }));
}

/**
 * @param {string} text
 * @param {number} offset
 * @param {Map<string, SpellingEntry[]>} spellingsByLatin
 * @returns {{word: string, start: number, end: number, items: Item[]} | null}
 */
function completions(text, offset, spellingsByLatin) {
  const latinWord = latinWordAt(text, offset);
  if (!latinWord) return null;
  let { start, end } = latinWord;
  let key = latinWord.word.toLowerCase().replace(CURLY, "'");
  let senses = spellingsByLatin.get(key);
  if (!senses) {
    const trimmed = key.replace(TRAILING, "");
    if (trimmed && LETTER.test(trimmed)) {
      end -= key.length - trimmed.length;
      key = trimmed;
      senses = spellingsByLatin.get(key);
    }
  }
  while (!senses) {
    const cut = key.indexOf(HYPHEN);
    if (cut < 0) break;
    start += cut + 1;
    key = key.slice(cut + 1);
    if (key && LETTER.test(key)) senses = spellingsByLatin.get(key);
  }
  if (!senses || offset < start || offset > end) return null;
  return { word: text.slice(start, end), start, end, items: items(senses) };
}

/**
 * @param {string} text
 * @param {Map<string, SpellingEntry[]>} spellingsByLatin
 * @returns {{latin: string, items: Item[]}[]}
 */
function lookupSpellings(text, spellingsByLatin) {
  /** @type {{latin: string, items: Item[]}[]} */
  const out = [];
  for (const [run] of text.matchAll(RUN)) {
    if (out.length >= MAX_LOOKUP_WORDS) break;
    if (!LETTER.test(run)) continue;
    const key = run.toLowerCase().replace(CURLY, "'").replace(TRAILING, "");
    const senses = spellingsByLatin.get(key);
    const pieces = senses || !key.includes(HYPHEN) ? [key] : key.split(HYPHEN);
    for (const piece of pieces) {
      if (!LETTER.test(piece)) continue;
      const matches = spellingsByLatin.get(piece);
      out.push({ latin: piece, items: matches ? items(matches) : [] });
    }
  }
  return out;
}

module.exports = { completions, latinWordAt, lookupSpellings };
