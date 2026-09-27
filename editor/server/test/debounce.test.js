const assert = require("node:assert/strict");
const { test } = require("node:test");
const { debouncer } = require("../lib/debounce.js");

test("rapid schedules coalesce into one run", (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  /** @type {string[]} */
  const ran = [];
  const pending = debouncer(200, (key) => ran.push(key));
  pending.schedule("a");
  t.mock.timers.tick(100);
  pending.schedule("a");
  t.mock.timers.tick(199);
  assert.deepEqual(ran, []);
  t.mock.timers.tick(1);
  assert.deepEqual(ran, ["a"]);
});

test("documents debounce independently", (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  /** @type {string[]} */
  const ran = [];
  const pending = debouncer(200, (key) => ran.push(key));
  pending.schedule("a");
  t.mock.timers.tick(100);
  pending.schedule("b");
  t.mock.timers.tick(100);
  assert.deepEqual(ran, ["a"]);
  t.mock.timers.tick(100);
  assert.deepEqual(ran, ["a", "b"]);
});

test("a canceled document never runs", (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  /** @type {string[]} */
  const ran = [];
  const pending = debouncer(200, (key) => ran.push(key));
  pending.schedule("a");
  pending.schedule("b");
  pending.cancel("a");
  t.mock.timers.tick(400);
  assert.deepEqual(ran, ["b"]);
});

test("clear drops everything pending", (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  /** @type {string[]} */
  const ran = [];
  const pending = debouncer(200, (key) => ran.push(key));
  pending.schedule("a");
  pending.schedule("b");
  pending.clear();
  t.mock.timers.tick(400);
  assert.deepEqual(ran, []);
  pending.schedule("c");
  t.mock.timers.tick(200);
  assert.deepEqual(ran, ["c"]);
});
