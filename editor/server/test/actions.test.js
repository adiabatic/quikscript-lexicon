const assert = require("node:assert/strict");
const { test } = require("node:test");
const data = require("../payload.json");
const { lexicon } = require("../lib/lexicon.js");
const core = require("../../../src/qslex/web/core.js");
const {
  COMMANDS,
  DIRECTORY,
  OCCURRENCE,
  PROJECT,
  USER,
  actions,
  cachedSuggester,
} = require("../lib/actions.js");

const WORDS = lexicon(data);
const GOOD = data.words.split("\n", 1)[0].split("\t", 1)[0];
const BAD = "\uE650".repeat(9);
const URI = "file:///draft/letter.md";

/**
 * @param {number} line
 * @param {number} from
 * @param {number} to
 */
function span(line, from, to) {
  return { start: { line, character: from }, end: { line, character: to } };
}

test("each offer becomes a materialized quickfix, the first preferred", () => {
  const flag = { word: BAD, occurrence: 0, range: span(0, 0, 9) };
  const everywhere = [span(0, 0, 9), span(2, 4, 13), span(5, 1, 10)];
  const offers = [GOOD, `${GOOD}-${GOOD}`];
  const out = actions(URI, flag, everywhere, offers, { directory: true, project: true });
  assert.deepEqual(
    out.map((action) => action.title),
    [
      GOOD,
      `${GOOD} — and the 2 others written the same way`,
      `${GOOD}-${GOOD}`,
      `${GOOD}-${GOOD} — and the 2 others written the same way`,
      "Ignore this occurrence",
      "Ignore in this directory",
      "Ignore in this project",
      "Ignore everywhere",
    ],
  );
  assert.deepEqual(out[0], {
    title: GOOD,
    kind: "quickfix",
    isPreferred: true,
    edit: { changes: { [URI]: [{ range: span(0, 0, 9), newText: GOOD }] } },
  });
  assert.deepEqual(out[1], {
    title: `${GOOD} — and the 2 others written the same way`,
    kind: "quickfix",
    edit: {
      changes: { [URI]: everywhere.map((span) => ({ range: span, newText: GOOD })) },
    },
  });
  assert.equal("isPreferred" in out[2], false);
});

test("a lone occurrence offers no fix-all, a pair speaks in the singular", () => {
  const flag = { word: BAD, occurrence: 0, range: span(0, 0, 9) };
  const lone = actions(URI, flag, [flag.range], [GOOD], { directory: false, project: false });
  assert.deepEqual(
    lone.map((action) => action.title),
    [GOOD, "Ignore this occurrence", "Ignore everywhere"],
  );
  const pair = actions(URI, flag, [flag.range, span(1, 0, 9)], [GOOD], {
    directory: false,
    project: false,
  });
  assert.equal(pair[1].title, `${GOOD} — and the 1 other written the same way`);
});

test("the ignore tiers ride as fully spelled-out commands", () => {
  const flag = { word: BAD, occurrence: 2, range: span(3, 1, 10) };
  const out = actions(URI, flag, [flag.range], [], { directory: true, project: true });
  assert.deepEqual(out, [
    {
      title: "Ignore this occurrence",
      kind: "quickfix",
      command: {
        title: "Ignore this occurrence",
        command: "quikscript.ignore.occurrence",
        arguments: [{ uri: URI, word: BAD, occurrence: 2 }],
      },
    },
    {
      title: "Ignore in this directory",
      kind: "quickfix",
      command: {
        title: "Ignore in this directory",
        command: "quikscript.ignore.directory",
        arguments: [{ uri: URI, word: BAD }],
      },
    },
    {
      title: "Ignore in this project",
      kind: "quickfix",
      command: {
        title: "Ignore in this project",
        command: "quikscript.ignore.project",
        arguments: [{ uri: URI, word: BAD }],
      },
    },
    {
      title: "Ignore everywhere",
      kind: "quickfix",
      command: {
        title: "Ignore everywhere",
        command: "quikscript.ignore.user",
        arguments: [{ word: BAD }],
      },
    },
  ]);
  assert.deepEqual(COMMANDS, [OCCURRENCE, DIRECTORY, PROJECT, USER]);
});

test("suggestions are computed once per word and served from the cache", () => {
  const offered = cachedSuggester(WORDS);
  const first = offered(BAD);
  assert.equal(offered(BAD), first);
  assert.deepEqual(
    first,
    core.suggest(BAD, {
      active: WORDS.active,
      freq: WORDS.counts,
      groups: WORDS.groups,
      letters: WORDS.letters,
      rep: WORDS.rep,
    }),
  );
});
