const assert = require("node:assert/strict");
const { test } = require("node:test");
const data = require("../payload.json");
const { faced, label, readings, writings } = require("../lib/lookup.js");

const READ = readings(data);
const WRITE = writings(data);

test("the readings key every union spelling and the writings every latin", () => {
  assert.equal(READ.size, data.words.split("\n").length);
  assert.equal(WRITE.size, 77545);
});

test("a reading names its row and the column the spelling sits in", () => {
  const held = READ.get("\uE668\uE671\uE653");
  assert.deepEqual(held, [
    { latin: "read", pos: "NN1", column: "senior" },
    { latin: "read", pos: "VVB", column: "senior" },
    { latin: "read", pos: "VVI", column: "senior" },
    { latin: "reade", pos: "NP0", column: "senior" },
    { latin: "reed", pos: "NN1", column: "senior" },
  ]);
});

test("a writing carries its tag, frequency, and three columns", () => {
  const rows = WRITE.get("couldn't");
  assert.deepEqual(rows, [
    {
      pos: "VM0+XX0",
      frequency: 0,
      senior: "\uE654\uE67D\uE653\uE666\uE652",
      junior: "\uE654\uE67D\uE653\uE67A\uE666\uE652",
      x: "",
    },
  ]);
  assert.equal(faced(rows[0], "senior"), rows[0].senior);
  assert.equal(faced(rows[0], "junior"), rows[0].junior);
  assert.equal(faced(rows[0], "x"), "");
});

test("labels name the obvious tags and pass the rest through raw", () => {
  assert.equal(label("NN1"), "singular noun");
  assert.equal(label("ITJ"), "interjection");
  assert.equal(label("VVD"), "past-tense verb");
  assert.equal(label("VM0+XX0"), "modal verb + not");
  assert.equal(label("PRE"), "PRE");
  assert.equal(label("UNC"), "UNC");
});
