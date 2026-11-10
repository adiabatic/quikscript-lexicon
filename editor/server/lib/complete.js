const { items } = require("../../../src/qslex/web/lookup.js");

const LETTER = /[A-Za-z]/;
const WORDY = /[A-Za-z'’-]/;
const CURLY = /’/g;
const TRAILING = /'+$/;
const HYPHEN = "-";

/** @typedef {import("../../../src/qslex/web/lookup.js").SpellingEntry} SpellingEntry */
/** @typedef {import("../../../src/qslex/web/lookup.js").Item} Item */

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

module.exports = { completions, latinWordAt };
