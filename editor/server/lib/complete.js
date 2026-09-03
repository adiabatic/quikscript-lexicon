const { FACE_OF, JUNIOR, SENIOR, X, faced, label } = require("./lookup.js");

const LETTER = /[A-Za-z]/;
const WORDY = /[A-Za-z'’-]/;
const CURLY = /’/g;
const TRAILING = /'+$/;
const HYPHEN = "-";
const RUN = /[A-Za-z'’-]+/g;
const MOST = 20;

/** @typedef {import("./lookup.js").Writing} Writing */
/** @typedef {{label: string, detail: string, sortText: string}} Item */

/**
 * @param {string} text
 * @param {number} offset
 * @returns {{word: string, start: number, end: number} | null}
 */
function worded(text, offset) {
  let start = Math.min(Math.max(offset, 0), text.length);
  let end = start;
  while (start > 0 && WORDY.test(text[start - 1])) start -= 1;
  while (end < text.length && WORDY.test(text[end])) end += 1;
  if (start === end) return null;
  const word = text.slice(start, end);
  return LETTER.test(word) ? { word, start, end } : null;
}

/**
 * @param {Writing[]} senses
 * @returns {Item[]}
 */
function items(senses) {
  /** @type {Map<string, {labels: string[], frequency: number, faces: Set<string>}>} */
  const merged = new Map();
  for (const sense of senses) {
    for (const face of [SENIOR, JUNIOR, X]) {
      const form = faced(sense, face);
      if (!form) continue;
      const named = label(sense.pos);
      const held = merged.get(form);
      if (held) {
        if (!held.labels.includes(named)) held.labels.push(named);
        held.frequency = Math.max(held.frequency, sense.frequency);
        held.faces.add(face);
      } else {
        merged.set(form, {
          labels: [named],
          frequency: sense.frequency,
          faces: new Set([face]),
        });
      }
    }
  }
  const ranked = [...merged].sort(
    ([oneForm, one], [otherForm, other]) =>
      other.frequency - one.frequency ||
      Number(!one.faces.has(SENIOR)) - Number(!other.faces.has(SENIOR)) ||
      (oneForm < otherForm ? -1 : 1),
  );
  return ranked.map(([form, held], at) => ({
    label: form,
    detail: held.faces.has(SENIOR)
      ? held.labels.join(", ")
      : `${held.labels.join(", ")} — ${[...held.faces]
          .map((face) => FACE_OF[face])
          .join(", ")} form`,
    sortText: String(at).padStart(4, "0"),
  }));
}

/**
 * @param {string} text
 * @param {number} offset
 * @param {Map<string, Writing[]>} write
 * @returns {{word: string, start: number, end: number, items: Item[]} | null}
 */
function completions(text, offset, write) {
  const held = worded(text, offset);
  if (!held) return null;
  let { start, end } = held;
  let key = held.word.toLowerCase().replace(CURLY, "'");
  let senses = write.get(key);
  if (!senses) {
    const trimmed = key.replace(TRAILING, "");
    if (trimmed && LETTER.test(trimmed)) {
      end -= key.length - trimmed.length;
      key = trimmed;
      senses = write.get(key);
    }
  }
  while (!senses) {
    const cut = key.indexOf(HYPHEN);
    if (cut < 0) break;
    start += cut + 1;
    key = key.slice(cut + 1);
    if (key && LETTER.test(key)) senses = write.get(key);
  }
  if (!senses || offset < start || offset > end) return null;
  return { word: text.slice(start, end), start, end, items: items(senses) };
}

/**
 * @param {string} text
 * @param {Map<string, Writing[]>} write
 * @returns {{latin: string, items: Item[]}[]}
 */
function written(text, write) {
  /** @type {{latin: string, items: Item[]}[]} */
  const out = [];
  for (const [run] of text.matchAll(RUN)) {
    if (out.length >= MOST) break;
    if (!LETTER.test(run)) continue;
    const key = run.toLowerCase().replace(CURLY, "'").replace(TRAILING, "");
    const senses = write.get(key);
    const pieces = senses || !key.includes(HYPHEN) ? [key] : key.split(HYPHEN);
    for (const piece of pieces) {
      if (!LETTER.test(piece)) continue;
      const held = write.get(piece);
      out.push({ latin: piece, items: held ? items(held) : [] });
    }
  }
  return out;
}

module.exports = { completions, worded, written };
