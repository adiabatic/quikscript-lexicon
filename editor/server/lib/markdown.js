const { stripFrontMatter } = require("../../../src/qslex/web/core.js");

const BREAK = /\r\n|\r|\n/g;
const OPENING = /^ {0,3}(`{3,}|~{3,})(.*)$/;
const CLOSING = /^ {0,3}(`{3,}|~{3,})[ \t]*$/;
const TICKS = /`+/g;
const BLANK = /(?:\r\n|\r|\n)[ \t]*(?:\r\n|\r|\n)/;

/** @typedef {{start: number, end: number}} Range */
/** @typedef {{start: number, end: number, stop: number}} Line */

/**
 * @param {string} text
 * @param {number} from
 * @returns {Line[]}
 */
function lines(text, from) {
  const out = [];
  let at = from;
  BREAK.lastIndex = from;
  for (let hit = BREAK.exec(text); hit !== null; hit = BREAK.exec(text)) {
    out.push({ start: at, end: hit.index, stop: BREAK.lastIndex });
    at = BREAK.lastIndex;
  }
  if (at < text.length) out.push({ start: at, end: text.length, stop: text.length });
  return out;
}

/**
 * @param {string} written
 * @param {{char: string, count: number}} fence
 * @returns {boolean}
 */
function closes(written, fence) {
  const closing = written.match(CLOSING);
  return (
    closing !== null &&
    closing[1][0] === fence.char &&
    closing[1].length >= fence.count
  );
}

/**
 * @param {string} text
 * @param {Range} span
 * @param {Range[]} ranges
 */
function inlineCode(text, span, ranges) {
  const region = text.slice(span.start, span.end);
  /** @type {Range[]} */
  const runs = [];
  TICKS.lastIndex = 0;
  for (let hit = TICKS.exec(region); hit !== null; hit = TICKS.exec(region)) {
    runs.push({ start: hit.index, end: TICKS.lastIndex });
  }
  for (let i = 0; i < runs.length; i += 1) {
    const opener = runs[i];
    const length = opener.end - opener.start;
    for (let j = i + 1; j < runs.length; j += 1) {
      const closer = runs[j];
      if (closer.end - closer.start !== length) continue;
      if (BLANK.test(region.slice(opener.end, closer.start))) break;
      ranges.push({ start: span.start + opener.start, end: span.start + closer.end });
      i = j;
      break;
    }
  }
}

/**
 * @param {string} text
 * @returns {Range[]}
 */
function skipRanges(text) {
  /** @type {Range[]} */
  const ranges = [];
  const lead = text.length - stripFrontMatter(text).length;
  if (lead > 0) ranges.push({ start: 0, end: lead });

  /** @type {{start: number, char: string, count: number} | null} */
  let fence = null;
  /** @type {Range[]} */
  const prose = [];
  let gap = lead;
  for (const line of lines(text, lead)) {
    const written = text.slice(line.start, line.end);
    if (fence) {
      if (closes(written, fence)) {
        ranges.push({ start: fence.start, end: line.stop });
        fence = null;
        gap = line.stop;
      }
      continue;
    }
    const opened = written.match(OPENING);
    if (!opened) continue;
    if (opened[1][0] === "`" && opened[2].includes("`")) continue;
    if (line.start > gap) prose.push({ start: gap, end: line.start });
    fence = { start: line.start, char: opened[1][0], count: opened[1].length };
  }
  if (fence) ranges.push({ start: fence.start, end: text.length });
  else if (text.length > gap) prose.push({ start: gap, end: text.length });

  for (const span of prose) inlineCode(text, span, ranges);
  ranges.sort((one, other) => one.start - other.start);
  return ranges;
}

module.exports = { skipRanges };
