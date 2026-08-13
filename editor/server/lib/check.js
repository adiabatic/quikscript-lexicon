const { accepts, tokens } = require("../../../src/qslex/web/core.js");
const { skipRanges } = require("./markdown.js");

const BREAK = /\r\n|\r|\n/g;
const MARKDOWN = "markdown";
const INFORMATION = /** @type {const} */ (3);
const SOURCE = "quikscript";
const UNKNOWN = "unknown-word";
const CAP = 500;

/** @typedef {{line: number, character: number}} Position */
/** @typedef {{start: Position, end: Position}} Span */
/** @typedef {{range: Span, severity: 1 | 2 | 3 | 4, source: string, code: string, message: string}} Diagnostic */

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
 * @param {string} text
 * @param {string} languageId
 * @param {Set<string>} active
 * @returns {Diagnostic[]}
 */
function diagnostics(text, languageId, active) {
  const skipped = languageId.toLowerCase() === MARKDOWN ? skipRanges(text) : [];
  const starts = lineStarts(text);
  /** @type {Diagnostic[]} */
  const out = [];
  let at = 0;
  for (const hit of tokens(text)) {
    if (out.length >= CAP) break;
    while (at < skipped.length && skipped[at].end <= hit.start) at += 1;
    if (at < skipped.length && skipped[at].start <= hit.start) continue;
    if (accepts(active, hit.word)) continue;
    out.push({
      range: { start: position(starts, hit.start), end: position(starts, hit.end) },
      severity: INFORMATION,
      source: SOURCE,
      code: UNKNOWN,
      message: `Unknown Quikscript spelling: ${hit.word}`,
    });
  }
  return out;
}

module.exports = { CAP, diagnostics };
