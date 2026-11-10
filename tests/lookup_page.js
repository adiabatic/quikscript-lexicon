const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const [PAGE] = process.argv.slice(2);
assert.ok(PAGE, "usage: node lookup_page.js <lookup.html>");
const page = fs.readFileSync(PAGE, "utf8");

const scripts = [];
for (let at = page.indexOf("<script>"); at >= 0; at = page.indexOf("<script>", at + 1)) {
  scripts.push(page.slice(at + "<script>".length, page.indexOf("</script>", at)));
}
assert.equal(scripts.length, 3, "the page runs data, then lookup, then the page script");
assert.ok(scripts[0].startsWith("const QS = "), "the data script is first");

const READ_EAT = "";
const READ_ET = "";
const HELLO = "";
const WORLD = "";
const DEBOUNCED_MS = 300;

class Element {
  constructor(tag) {
    this.tagName = tag.toUpperCase();
    this.className = "";
    this.childNodes = [];
    this.handlers = new Map();
    this.text = "";
    this.value = "";
  }

  get textContent() {
    return this.text + this.childNodes.map((node) => node.textContent).join("");
  }

  set textContent(value) {
    this.text = value;
    this.childNodes = [];
  }

  append(...nodes) {
    for (const node of nodes) {
      this.childNodes.push(typeof node === "string" ? { textContent: node } : node);
    }
  }

  replaceChildren(...nodes) {
    this.text = "";
    this.childNodes = [];
    this.append(...nodes);
  }

  addEventListener(kind, listener) {
    if (!this.handlers.has(kind)) this.handlers.set(kind, []);
    this.handlers.get(kind).push(listener);
  }

  fire(kind) {
    const listeners = this.handlers.get(kind) || [];
    assert.ok(listeners.length > 0, `nothing listens for ${kind}`);
    for (const listener of listeners) listener({ target: this, preventDefault() {} });
  }

  click() {
    this.fire("click");
  }

  querySelector(selector) {
    assert.equal(selector, "button", "the shim only finds buttons");
    for (const node of this.childNodes) {
      if (node.tagName === "BUTTON") return node;
      const found = node.querySelector?.(selector);
      if (found) return found;
    }
    return null;
  }
}

function loadPage(clipboard) {
  const parts = {
    latin: new Element("input"),
    lookup: new Element("form"),
    results: new Element("div"),
    status: new Element("p"),
  };
  const selection = { node: null };
  const box = {
    setTimeout,
    clearTimeout,
    navigator: { clipboard, platform: "MacIntel" },
    getSelection: () => ({
      selectAllChildren(node) {
        selection.node = node;
      },
    }),
    document: {
      getElementById: (id) => parts[id] || null,
      createElement: (tag) => new Element(tag),
    },
  };
  box.window = box;
  vm.createContext(box);
  for (const [at, code] of scripts.entries()) {
    vm.runInContext(code, box, { filename: `script-${at}.js` });
  }
  return { parts, selection };
}

function rows(results) {
  return results.childNodes.map((node) =>
    node.tagName === "BUTTON"
      ? node.childNodes.map((child) => child.textContent)
      : [node.className, node.textContent],
  );
}

function type(parts, value) {
  parts.latin.value = value;
  parts.latin.fire("input");
}

const settle = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const done = [];
async function check(name, body) {
  try {
    await body();
  } catch (failure) {
    for (const each of done) console.log(`ok    ${each}`);
    console.log(`FAIL  ${name}`);
    throw failure;
  }
  done.push(name);
}

let copied = null;
const clipboard = {
  writeText(text) {
    copied = text;
    return Promise.resolve();
  },
};

(async () => {
  await check("a typed word lists each of its spellings with its gloss once the debounce has elapsed", async () => {
    const { parts } = loadPage(clipboard);
    type(parts, "Read");
    assert.deepEqual(rows(parts.results), []);
    await settle(DEBOUNCED_MS);
    assert.deepEqual(rows(parts.results), [
      [READ_EAT, "singular noun, verb, infinitive"],
      [READ_ET, "past-tense verb, past participle"],
    ]);
  });

  await check("a phrase whose words all have spellings starts with the whole phrase", async () => {
    const { parts } = loadPage(clipboard);
    type(parts, "Hello, world");
    await settle(DEBOUNCED_MS);
    assert.deepEqual(rows(parts.results), [
      [`${HELLO} ${WORLD}`],
      [HELLO, "hello — interjection"],
      [WORLD, "world — singular noun"],
    ]);
  });

  await check("a word with no spelling gets a note and the phrase is not spelled", async () => {
    const { parts } = loadPage(clipboard);
    type(parts, "hello zzxq");
    await settle(DEBOUNCED_MS);
    assert.deepEqual(rows(parts.results), [
      [HELLO, "hello — interjection"],
      ["note", "No spelling for zzxq"],
    ]);
  });

  await check("clicking a spelling copies it and names it in the status", async () => {
    const { parts } = loadPage(clipboard);
    type(parts, "read");
    await settle(DEBOUNCED_MS);
    copied = null;
    parts.results.childNodes[1].click();
    await settle(0);
    assert.equal(copied, READ_ET);
    assert.equal(parts.status.textContent, `Copied${READ_ET}`);
  });

  await check("Enter copies the first spelling of what is typed without waiting for the debounce", async () => {
    const { parts } = loadPage(clipboard);
    copied = null;
    type(parts, "hello world");
    parts.lookup.fire("submit");
    await settle(0);
    assert.equal(copied, `${HELLO} ${WORLD}`);
  });

  await check("without a clipboard, clicking selects the spelling and says how to copy it", async () => {
    const { parts, selection } = loadPage(undefined);
    type(parts, "read");
    await settle(DEBOUNCED_MS);
    const button = parts.results.childNodes[0];
    button.click();
    assert.equal(selection.node, button.childNodes[0]);
    assert.equal(parts.status.textContent, "Press ⌘C to copy");
  });

  for (const each of done) console.log(`ok    ${each}`);
  console.log(`\n${done.length} checks passed`);
})().catch((failure) => {
  console.error(failure);
  process.exit(1);
});
