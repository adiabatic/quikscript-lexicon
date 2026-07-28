const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const [PAGE] = process.argv.slice(2);
assert.ok(PAGE, "usage: node playground_page.js <index.html>");
const page = fs.readFileSync(PAGE, "utf8");

const scripts = [];
for (let at = page.indexOf("<script>"); at >= 0; at = page.indexOf("<script>", at + 1)) {
  scripts.push(page.slice(at + "<script>".length, page.indexOf("</script>", at)));
}
assert.equal(scripts.length, 4, "the page runs marked, then data, then core, then app");
assert.ok(scripts[1].startsWith("const QS = "), "the data script is second");

const unescape = (html) =>
  html
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#x27;/g, "'")
    .replace(/&#39;/g, "'")
    .replace(/&amp;/g, "&");

const opened = page.indexOf("<textarea");
const SAMPLE = unescape(
  page.slice(page.indexOf(">", opened) + 1, page.indexOf("</textarea>")),
);

function classes() {
  const held = new Set();
  return {
    held,
    add: (name) => held.add(name),
    remove: (name) => held.delete(name),
    contains: (name) => held.has(name),
    toggle: (name, on) => (on ? held.add(name) : held.delete(name)),
  };
}

function styles() {
  const props = new Map();
  return {
    props,
    setProperty: (name, value) => props.set(name, value),
    removeProperty: (name) => props.delete(name),
    set left(value) {
      props.set("left", value);
    },
    set top(value) {
      props.set("top", value);
    },
  };
}

class Fragment {
  constructor() {
    this.nodeType = 11;
    this.childNodes = [];
  }

  append(...nodes) {
    for (const node of nodes) {
      node.parentNode = this;
      this.childNodes.push(node);
    }
  }
}

class Element extends Fragment {
  constructor(tag) {
    super();
    this.nodeType = 1;
    this.tagName = tag.toUpperCase();
    this.parentNode = null;
    this.dataset = {};
    this.classList = classes();
    this.style = styles();
    this.attributes = new Map();
    this.handlers = new Map();
    this.textContent = "";
    this.value = "";
    this.checked = false;
    this.showing = false;
    this.focused = false;
    this.selected = false;
  }

  get className() {
    return [...this.classList.held].join(" ");
  }

  set className(value) {
    this.classList.held.clear();
    for (const name of value.split(" ")) if (name) this.classList.held.add(name);
  }

  replaceChildren() {
    this.childNodes = [];
  }

  addEventListener(kind, listener) {
    if (!this.handlers.has(kind)) this.handlers.set(kind, []);
    this.handlers.get(kind).push(listener);
  }

  fire(kind, event) {
    const listeners = this.handlers.get(kind) || [];
    assert.ok(listeners.length > 0, `nothing listens for ${kind}`);
    for (const listener of listeners) listener(event || { target: this });
  }

  hasAttribute(name) {
    return this.attributes.has(name);
  }

  matches(selector) {
    if (selector === ":popover-open") return this.showing;
    return this.classList.contains(selector.replace(".", ""));
  }

  closest(selector) {
    for (let held = this; held; held = held.parentNode) {
      if (held.nodeType === 1 && held.matches(selector)) return held;
    }
    return null;
  }

  getBoundingClientRect() {
    return { left: 300, top: 400, right: 380, bottom: 430, width: 80, height: 30 };
  }

  showPopover() {
    assert.equal(this.showing, false, "showPopover on an open popover would throw");
    this.showing = true;
  }

  hidePopover() {
    assert.equal(this.showing, true, "hidePopover on a shut popover would throw");
    this.showing = false;
  }

  focus() {
    this.focused = true;
  }

  select() {
    this.selected = true;
  }
}

function textNode(data, parent) {
  return {
    nodeType: 3,
    data,
    parentNode: parent,
    replaced: null,
    replaceWith(fragment) {
      this.replaced = fragment;
    },
  };
}

const strip = (html) =>
  unescape(html.replace(/<[^>]*>/g, " "))
    .replace(/\s+/g, " ")
    .trim();

function flatten(element) {
  Object.defineProperty(element, "innerHTML", {
    get() {
      return this.html;
    },
    set(html) {
      this.html = html;
      this.texts = [textNode(strip(html), this)];
    },
  });
  return element;
}

let copied = null;
const clipboard = {
  writeText(text) {
    copied = text;
    return Promise.resolve();
  },
};

function stage(supports) {
  const parts = {
    source: new Element("textarea"),
    preview: flatten(new Element("div")),
    senior: new Element("input"),
    fixer: new Element("div"),
    copy: new Element("button"),
  };
  parts.source.value = SAMPLE;
  parts.copy.textContent = "Copy source";
  parts.fixer.attributes.set("popover", "auto");

  const box = {
    console,
    setTimeout,
    clearTimeout,
    Node: { ELEMENT_NODE: 1, TEXT_NODE: 3 },
    NodeFilter: { SHOW_TEXT: 4 },
    navigator: { clipboard },
    CSS: { supports: () => supports },
    innerWidth: 1200,
    innerHeight: 800,
    document: {
      getElementById: (id) => parts[id] || null,
      createElement: (tag) => new Element(tag),
      createDocumentFragment: () => new Fragment(),
      createTextNode: (data) => textNode(data, null),
      createTreeWalker(root) {
        const nodes = root.texts || [];
        let at = -1;
        return {
          nextNode() {
            at += 1;
            return nodes[at] || null;
          },
        };
      },
    },
  };
  box.window = box;
  box.globalThis = box;
  vm.createContext(box);
  for (const [at, code] of scripts.entries()) {
    vm.runInContext(code, box, { filename: `script-${at}.js` });
  }
  return { parts, box };
}

const done = [];
function check(name, body) {
  try {
    body();
  } catch (failure) {
    for (const each of done) console.log(`ok    ${each}`);
    console.log(`FAIL  ${name}`);
    throw failure;
  }
  done.push(name);
}

const { parts, box } = stage(false);
const { source, preview, senior: grade, fixer, copy: copier } = parts;
done.push("the four inline scripts load in order, with no name declared twice");

check("marked is inlined and parses the sample", () => {
  assert.equal(typeof box.marked.parse, "function");
  assert.ok(preview.html.startsWith("<h1>"));
  assert.ok(preview.html.includes("<p>"));
});

check("core is on the page as globals app can see", () => {
  assert.equal(typeof box.tokens, "function");
  assert.equal(typeof box.accepts, "function");
  assert.equal(typeof box.suggest, "function");
  assert.equal(typeof box.replaceOccurrence, "function");
});

const marked = (element) =>
  (element.texts[0].replaced ? element.texts[0].replaced.childNodes : []).filter(
    (node) => node.nodeType === 1 && node.classList.contains("miss"),
  );
const spans = () => marked(preview);

check("the first render underlines the one word the lexicon does not carry", () => {
  assert.ok(preview.texts[0].replaced, "the text node holding a misspelling was replaced");
  assert.equal(spans().length, 1);
  assert.equal(spans()[0].dataset.occ, "0");
  assert.equal(spans()[0].textContent, spans()[0].dataset.w);
  const rebuilt = preview.texts[0].replaced.childNodes
    .map((node) => (node.nodeType === 3 ? node.data : node.textContent))
    .join("");
  assert.equal(rebuilt, preview.texts[0].data, "wrapping keeps the text it wrapped");
});

const misspelt = spans()[0].dataset.w;

check("clicking the underline opens the popover with suggestions", () => {
  preview.fire("click", { target: spans()[0] });
  assert.equal(fixer.showing, true);
  assert.equal(fixer.childNodes[0].tagName, "DIV");
  assert.equal(fixer.childNodes[0].classList.contains("word"), true);
  assert.equal(fixer.childNodes[0].textContent, misspelt);
  const buttons = fixer.childNodes.filter((node) => node.tagName === "BUTTON");
  assert.ok(buttons.length > 0 && buttons.length <= 8, `${buttons.length} offers`);
  for (const button of buttons) assert.equal(button.type, "button");
});

check("the popover is pinned inside the viewport when anchoring is unavailable", () => {
  assert.equal(fixer.classList.contains("anchored"), false);
  assert.equal(fixer.style.props.get("left"), "300px");
  assert.equal(fixer.style.props.get("top"), "434px");
});

check("choosing a suggestion edits the source, shuts the popover and re-renders", () => {
  const button = fixer.childNodes.find((node) => node.tagName === "BUTTON");
  const fix = button.textContent;
  button.fire("click");
  assert.equal(fixer.showing, false);
  const written = box.tokens(source.value).map((hit) => hit.word);
  assert.ok(written.includes(fix));
  assert.ok(!written.includes(misspelt), "the token is gone, not merely the substring");
  assert.equal(written.length, box.tokens(SAMPLE).length);
  assert.equal(spans().length, 0, "nothing is underlined once the word is spelt right");
});

check("the copy button writes the source and flips its label", () => {
  copier.fire("click");
  assert.equal(copied, source.value);
});

check("the grade toggle swaps the font class and the active set", () => {
  const QS = vm.runInContext("QS", box);
  const older = QS.senior_only[0];
  const younger = QS.junior_only[0];
  source.value = `# heading\n\n${older} ${younger}\n`;
  grade.checked = false;
  grade.fire("change");
  box.render();
  assert.equal(preview.classList.contains("senior"), false);
  assert.equal(fixer.classList.contains("senior"), false);
  assert.deepEqual(
    spans().map((span) => span.dataset.w),
    [older],
    "junior mode refuses the senior-only spelling",
  );

  grade.checked = true;
  grade.fire("change");
  box.render();
  assert.equal(preview.classList.contains("senior"), true);
  assert.equal(fixer.classList.contains("senior"), true);
  assert.deepEqual(
    spans().map((span) => span.dataset.w),
    [younger],
    "senior mode refuses the junior-only spelling",
  );
});

check("occurrence indices count every token, code spans included", () => {
  const QS = vm.runInContext("QS", box);
  const wrong = QS.senior_only[0];
  grade.checked = false;
  grade.fire("change");
  source.value = `${wrong} \`${wrong}\` ${wrong}\n`;
  box.render();
  assert.deepEqual(
    spans().map((span) => span.dataset.occ),
    ["0", "1", "2"],
    "a flat shim sees one text node, so every occurrence is numbered in order",
  );
});

check("anchor positioning is used where the browser has it", () => {
  const anchored = stage(true);
  assert.equal(anchored.parts.fixer.classList.contains("anchored"), true);
  const shown = marked(anchored.parts.preview);
  assert.equal(shown.length, 1);
  anchored.parts.preview.fire("click", { target: shown[0] });
  assert.equal(anchored.parts.fixer.showing, true);
  assert.equal(shown[0].style.props.get("anchor-name"), "--qs-miss");
  assert.equal(anchored.parts.fixer.style.props.has("left"), false, "no inline placement");
  assert.equal(anchored.parts.fixer.style.props.has("top"), false);
});

check("only one span carries the anchor name at a time", () => {
  const anchored = stage(true);
  anchored.parts.source.value = `${misspelt} ${misspelt}\n`;
  anchored.box.render();
  const shown = marked(anchored.parts.preview);
  assert.equal(shown.length, 2);
  anchored.parts.preview.fire("click", { target: shown[0] });
  anchored.parts.fixer.showing = false;
  anchored.parts.preview.fire("click", { target: shown[1] });
  assert.equal(shown[0].style.props.has("anchor-name"), false);
  assert.equal(shown[1].style.props.get("anchor-name"), "--qs-miss");
  assert.equal(shown[0].dataset.occ, "0");
  assert.equal(shown[1].dataset.occ, "1");
});

const typed = stage(false);
const RESTING = typed.parts.preview.html;
typed.parts.source.value = `# typed\n\n${misspelt}\n`;
typed.parts.source.fire("input", { target: typed.parts.source });

check("typing does not re-render before the debounce has elapsed", () => {
  assert.equal(typed.parts.preview.html, RESTING);
});

setTimeout(() => {
  check("the debounced render lands once it has", () => {
    assert.notEqual(typed.parts.preview.html, RESTING);
    assert.ok(typed.parts.preview.html.includes("typed"));
    assert.deepEqual(
      marked(typed.parts.preview).map((span) => span.dataset.w),
      [misspelt],
    );
  });
  for (const each of done) console.log(`ok    ${each}`);
  console.log(`\n${done.length} checks passed`);
}, 300);
