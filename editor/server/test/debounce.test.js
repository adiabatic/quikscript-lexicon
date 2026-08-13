const assert = require("node:assert/strict");
const { test } = require("node:test");
const { debouncer } = require("../lib/debounce.js");

test("rapid schedules coalesce into one run", (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  /** @type {string[]} */
  const ran = [];
  const held = debouncer(200, (key) => ran.push(key));
  held.schedule("a");
  t.mock.timers.tick(100);
  held.schedule("a");
  t.mock.timers.tick(199);
  assert.deepEqual(ran, []);
  t.mock.timers.tick(1);
  assert.deepEqual(ran, ["a"]);
});

test("documents debounce independently", (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  /** @type {string[]} */
  const ran = [];
  const held = debouncer(200, (key) => ran.push(key));
  held.schedule("a");
  t.mock.timers.tick(100);
  held.schedule("b");
  t.mock.timers.tick(100);
  assert.deepEqual(ran, ["a"]);
  t.mock.timers.tick(100);
  assert.deepEqual(ran, ["a", "b"]);
});

test("a canceled document never runs", (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  /** @type {string[]} */
  const ran = [];
  const held = debouncer(200, (key) => ran.push(key));
  held.schedule("a");
  held.schedule("b");
  held.cancel("a");
  t.mock.timers.tick(400);
  assert.deepEqual(ran, ["b"]);
});

test("clear drops everything pending", (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  /** @type {string[]} */
  const ran = [];
  const held = debouncer(200, (key) => ran.push(key));
  held.schedule("a");
  held.schedule("b");
  held.clear();
  t.mock.timers.tick(400);
  assert.deepEqual(ran, []);
  held.schedule("c");
  t.mock.timers.tick(200);
  assert.deepEqual(ran, ["c"]);
});
