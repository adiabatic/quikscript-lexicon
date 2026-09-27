const { accepts, tokens } = require("../../../src/qslex/web/core.js");
const { skipRanges } = require("./markdown.js");

const BREAK = /\r\n|\r|\n/g;
const MARKDOWN = "markdown";
const INFORMATION = /** @type {const} */ (3);
const SOURCE = "quikscript";
const UNKNOWN = "unknown-word";
const MAX_DIAGNOSTICS = 500;

/** @typedef {{line: number, character: number}} Position */
/** @typedef {{start: Position, end: Position}} Span */
/** @typedef {{word: string, occurrence: number, start: number, end: number}} Hit */
/** @typedef {{range: Span, severity: 1 | 2 | 3 | 4, source: string, code: string, message: string, codeActions?: import("./actions.js").Action[]}} Diagnostic */

/**
 * @param {string} word
 * @param {number} occurrence
 * @returns {string}
 */
function occurrenceKey(word, occurrence) {
  return `${word}\t${occurrence}`;
}

/**
 * @param {string} text
 * @returns {number[]}
 */
function lineStarts(text) {
  const starts = [0];
  BREAK.lastIndex = 0;
  for (let hit = BREAK.exec(text); hit !== null; hit = BREAK.exec(text)) {
    starts.push(BREAK.lastIndex);
  }
  return starts;
}

/**
 * @param {number[]} starts
 * @param {number} offset
 * @returns {Position}
 */
function position(starts, offset) {
  let low = 0;
  let high = starts.length - 1;
  while (low < high) {
    const middle = (low + high + 1) >> 1;
    if (starts[middle] <= offset) low = middle;
    else high = middle - 1;
  }
  return { line: low, character: offset - starts[low] };
}

/**
 * @param {number[]} starts
 * @param {string} text
 * @param {Position} place
 * @returns {number}
 */
function offsetAt(starts, text, place) {
  if (place.line < 0 || place.line >= starts.length) return text.length;
  const from = starts[place.line];
  const upto = place.line + 1 < starts.length ? starts[place.line + 1] : text.length;
  let offset = Math.min(from + Math.max(place.character, 0), upto);
  while (offset > from && (text[offset - 1] === "\r" || text[offset - 1] === "\n")) {
    offset -= 1;
  }
  return offset;
}

/**
 * @param {string} text
 * @param {string} languageId
 * @param {Set<string>} active
 * @param {Set<string>} [ignoredWords]
 * @param {Set<string>} [ignoredOccurrences]
 * @returns {Hit[]}
 */
function flagged(
  text,
  languageId,
  active,
  ignoredWords = new Set(),
  ignoredOccurrences = new Set(),
) {
  const skipped = languageId.toLowerCase() === MARKDOWN ? skipRanges(text) : [];
  /** @type {Hit[]} */
  const out = [];
  /** @type {Map<string, number>} */
  const seen = new Map();
  let at = 0;
  for (const hit of tokens(text)) {
    if (out.length >= MAX_DIAGNOSTICS) break;
    const occurrence = seen.get(hit.word) || 0;
    seen.set(hit.word, occurrence + 1);
    while (at < skipped.length && skipped[at].end <= hit.start) at += 1;
    if (at < skipped.length && skipped[at].start <= hit.start) continue;
    if (accepts(active, hit.word)) continue;
    if (ignoredWords.has(hit.word)) continue;
    if (ignoredOccurrences.has(occurrenceKey(hit.word, occurrence))) continue;
    out.push({ word: hit.word, occurrence, start: hit.start, end: hit.end });
  }
  return out;
}

/**
 * @param {string} text
 * @param {Hit[]} hits
 * @returns {Diagnostic[]}
 */
function diagnostics(text, hits) {
  const starts = lineStarts(text);
  return hits.map((hit) => ({
    range: { start: position(starts, hit.start), end: position(starts, hit.end) },
    severity: INFORMATION,
    source: SOURCE,
    code: UNKNOWN,
    message: `Unknown Quikscript spelling: ${hit.word}`,
  }));
}

module.exports = { MAX_DIAGNOSTICS, diagnostics, flagged, lineStarts, occurrenceKey, offsetAt, position };
