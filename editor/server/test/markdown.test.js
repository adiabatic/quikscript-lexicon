const assert = require("node:assert/strict");
const { test } = require("node:test");
const { skipRanges } = require("../lib/markdown.js");

const QS = "\uE650\uE651\uE652";

test("plain prose has nothing to skip", () => {
  assert.deepEqual(skipRanges(""), []);
  assert.deepEqual(skipRanges(`some latin and ${QS} prose\n`), []);
});

test("front matter is skipped to the closing delimiter", () => {
  const text = `---\nqs: ${QS}\n---\n${QS}\n`;
  assert.deepEqual(skipRanges(text), [{ start: 0, end: text.indexOf(QS, 9) }]);
});

test("a backtick fence is skipped through its closing line", () => {
  const text = `${QS}\n\`\`\`\n${QS}\n\`\`\`\n${QS}\n`;
  assert.deepEqual(skipRanges(text), [{ start: 4, end: text.length - 4 }]);
});

test("a tilde fence may have an info string with backticks", () => {
  const text = `~~~ quik \`s\`\n${QS}\n~~~\n`;
  assert.deepEqual(skipRanges(text), [{ start: 0, end: text.length }]);
});

test("a backtick fence whose info string has a backtick is not a fence", () => {
  const text = "``` `\n";
  assert.deepEqual(skipRanges(text), []);
});

test("an unclosed fence runs to the end of the text", () => {
  const text = `\`\`\`\n${QS}`;
  assert.deepEqual(skipRanges(text), [{ start: 0, end: text.length }]);
});

test("a closing fence must be at least as long as its opener", () => {
  const text = `\`\`\`\`\n${QS}\n\`\`\`\n${QS}\n\`\`\`\`\n`;
  assert.deepEqual(skipRanges(text), [{ start: 0, end: text.length }]);
});

test("a fence closes only on its own character", () => {
  const text = `~~~\n${QS}\n\`\`\`\n${QS}\n~~~\n`;
  assert.deepEqual(skipRanges(text), [{ start: 0, end: text.length }]);
});

test("a fence indented four spaces is not a fence", () => {
  const text = `    \`\`\`\n${QS}\n`;
  assert.deepEqual(skipRanges(text), []);
});

test("an indented code block is not skipped", () => {
  assert.deepEqual(skipRanges(`para\n\n    ${QS}\n`), []);
});

test("an inline code span is skipped with its backticks", () => {
  const text = `${QS} \`${QS}\` ${QS}\n`;
  assert.deepEqual(skipRanges(text), [{ start: 4, end: 9 }]);
});

test("a double-backtick span may contain a single backtick", () => {
  const text = `\`\` \` ${QS} \`\` tail\n`;
  assert.deepEqual(skipRanges(text), [{ start: 0, end: 11 }]);
});

test("an unmatched backtick is literal", () => {
  assert.deepEqual(skipRanges(`a \` lone ${QS}\n`), []);
});

test("a code span cannot cross a blank line", () => {
  assert.deepEqual(skipRanges(`\`${QS}\n\n${QS}\`\n`), []);
});

test("a code span may cross a soft break", () => {
  const text = `\`${QS}\n${QS}\` tail\n`;
  assert.deepEqual(skipRanges(text), [{ start: 0, end: 9 }]);
});

test("backticks inside a fence open no span outside it", () => {
  const text = `\`\`\`\n\`${QS}\n\`\`\`\n${QS} \`code\`\n`;
  assert.deepEqual(skipRanges(text), [
    { start: 0, end: 13 },
    { start: 17, end: 23 },
  ]);
});

test("carriage-return line endings delimit fences and blank lines", () => {
  const crlf = `\`\`\`\r\n${QS}\r\n\`\`\`\r\n`;
  assert.deepEqual(skipRanges(crlf), [{ start: 0, end: crlf.length }]);
  const cr = `\`\`\`\r${QS}\r\`\`\`\r${QS}\r`;
  assert.deepEqual(skipRanges(cr), [{ start: 0, end: 12 }]);
  assert.deepEqual(skipRanges(`\`${QS}\r\r${QS}\`\r`), []);
});
