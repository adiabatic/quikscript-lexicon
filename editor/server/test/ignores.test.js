const assert = require("node:assert/strict");
const { test, before, after } = require("node:test");
const { mkdirSync, mkdtempSync, readFileSync, rmSync, utimesSync, writeFileSync } = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const {
  ancestorIgnorePaths,
  ignoreFileCache,
  projectIgnorePath,
  userIgnorePath,
} = require("../lib/ignores.js");

const ROOT = path.join(__dirname, "..", "..", "..");
let scratch = "";

before(() => {
  mkdirSync(path.join(ROOT, "tmp"), { recursive: true });
  scratch = mkdtempSync(path.join(ROOT, "tmp", "quikscript-ignores-"));
});

after(() => {
  rmSync(scratch, { recursive: true, force: true });
});

test("the user file is under XDG_CONFIG_HOME, or ~/.config by default", () => {
  assert.equal(
    userIgnorePath({ XDG_CONFIG_HOME: "/somewhere" }),
    path.join("/somewhere", "quikscript", "ignore"),
  );
  assert.equal(
    userIgnorePath({}),
    path.join(os.homedir(), ".config", "quikscript", "ignore"),
  );
});

test("ancestorIgnorePaths lists an ignore file for every directory up to the root", () => {
  const paths = ancestorIgnorePaths(path.join("/a", "b", "c"));
  assert.deepEqual(paths, [
    path.join("/a", "b", "c", ".quikscript-ignore"),
    path.join("/a", "b", ".quikscript-ignore"),
    path.join("/a", ".quikscript-ignore"),
    path.join("/", ".quikscript-ignore"),
  ]);
});

test("reading returns the union of every existing file and skips missing ones", () => {
  const deep = path.join(scratch, "one", "two", "three");
  mkdirSync(deep, { recursive: true });
  writeFileSync(projectIgnorePath(path.join(scratch, "one")), "  \uE650  \r\n\uE651\r\n\r\n");
  writeFileSync(projectIgnorePath(deep), "\uE652\n");
  const user = path.join(scratch, "config", "quikscript", "ignore");
  mkdirSync(path.dirname(user), { recursive: true });
  writeFileSync(user, "\uE653\n");
  const files = ignoreFileCache();
  const sources = [
    projectIgnorePath(deep),
    projectIgnorePath(path.join(scratch, "one", "two")),
    projectIgnorePath(path.join(scratch, "one")),
    user,
  ];
  assert.deepEqual([...files.read(sources)].sort(), ["\uE650", "\uE651", "\uE652", "\uE653"]);
});

test("an edited file is re-read when its mtime changes", () => {
  const home = path.join(scratch, "mtime");
  mkdirSync(home, { recursive: true });
  const file = projectIgnorePath(home);
  const files = ignoreFileCache();
  writeFileSync(file, "\uE650\n");
  utimesSync(file, new Date(1000000000000), new Date(1000000000000));
  assert.deepEqual([...files.read([file])], ["\uE650"]);
  writeFileSync(file, "\uE651\n");
  utimesSync(file, new Date(1100000000000), new Date(1100000000000));
  assert.deepEqual([...files.read([file])], ["\uE651"]);
});

test("appending is idempotent and makes the directories it needs", () => {
  const file = path.join(scratch, "made", "up", "ignore");
  const files = ignoreFileCache();
  assert.deepEqual([...files.read([file])], []);
  files.append(file, "\uE650");
  files.append(file, "\uE650");
  assert.equal(readFileSync(file, "utf8"), "\uE650\n");
  assert.deepEqual([...files.read([file])], ["\uE650"]);
});

test("appending completes a file that ends mid-line", () => {
  const home = path.join(scratch, "midline");
  mkdirSync(home, { recursive: true });
  const file = projectIgnorePath(home);
  writeFileSync(file, "\uE650");
  const files = ignoreFileCache();
  files.append(file, "\uE651");
  assert.equal(readFileSync(file, "utf8"), "\uE650\n\uE651\n");
  files.append(file, "\uE650");
  assert.equal(readFileSync(file, "utf8"), "\uE650\n\uE651\n");
});
