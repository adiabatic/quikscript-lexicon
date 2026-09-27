const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const [PAGE] = process.argv.slice(2);
assert.ok(PAGE, "usage: node desk_page.js <index.html>");
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
    this.hidden = false;
    this.showing = false;
    this.focused = false;
    this.selected = false;
    this.selectionStart = 0;
    this.selectionEnd = 0;
    this.selectionDirection = "none";
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
    const dispatched = event || { target: this };
    if (!("preventDefault" in dispatched)) dispatched.preventDefault = () => {};
    for (const listener of listeners) listener(dispatched);
  }

  hasAttribute(name) {
    return this.attributes.has(name);
  }

  setAttribute(name, value) {
    this.attributes.set(name, String(value));
  }

  getAttribute(name) {
    return this.attributes.has(name) ? this.attributes.get(name) : null;
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

  setSelectionRange(start, end, direction) {
    this.selectionStart = start;
    this.selectionEnd = end;
    this.selectionDirection = direction;
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

const KEPT = "qs-desk.ignored";
const CHOSEN = "qs-desk.senior";

function storage() {
  const held = new Map();
  return {
    held,
    getItem: (key) => (held.has(key) ? held.get(key) : null),
    setItem: (key, value) => held.set(key, String(value)),
  };
}

const sealed = {
  getItem() {
    throw new Error("this origin has no storage");
  },
  setItem() {
    throw new Error("this origin has no storage");
  },
};

function stage(supports, kept, platform = "MacIntel") {
  const parts = {
    source: new Element("textarea"),
    preview: flatten(new Element("div")),
    grade: new Element("button"),
    popover: new Element("div"),
    copy: new Element("button"),
    undo: new Element("button"),
    ignored: new Element("button"),
  };
  parts.source.value = SAMPLE;
  parts.copy.textContent = "Copy source";
  parts.popover.attributes.set("popover", "auto");

  const documentHandlers = new Map();
  const document = {
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
    addEventListener(kind, listener) {
      if (!documentHandlers.has(kind)) documentHandlers.set(kind, []);
      documentHandlers.get(kind).push(listener);
    },
    fire(kind, event) {
      const listeners = documentHandlers.get(kind) || [];
      assert.ok(listeners.length > 0, `nothing listens for document ${kind}`);
      for (const listener of listeners) listener(event);
    },
  };

  const box = {
    console,
    setTimeout,
    clearTimeout,
    Node: { ELEMENT_NODE: 1, TEXT_NODE: 3 },
    NodeFilter: { SHOW_TEXT: 4 },
    navigator: { clipboard, platform },
    localStorage: kept || storage(),
    CSS: { supports: () => supports },
    innerWidth: 1200,
    innerHeight: 800,
    document,
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
const { source, preview, grade, popover, copy: copyButton } = parts;
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

const misspelled = spans()[0].dataset.w;

const buttonsOf = (element) =>
  element.childNodes.flatMap((node) =>
    node.tagName === "BUTTON"
      ? [node]
      : (node.childNodes || []).filter((held) => held.tagName === "BUTTON"),
  );
const offersOf = (element) =>
  buttonsOf(element).filter(
    (node) => !node.classList.contains("ignore") && !node.classList.contains("fix-all"),
  );
const sweepersOf = (element) =>
  buttonsOf(element).filter((node) => node.classList.contains("fix-all"));
const ignoreOf = (element) =>
  buttonsOf(element).filter((node) => node.classList.contains("ignore"));

check("clicking the underline opens the popover with suggestions", () => {
  preview.fire("click", { target: spans()[0] });
  assert.equal(popover.showing, true);
  assert.equal(popover.childNodes[0].tagName, "DIV");
  assert.equal(popover.childNodes[0].classList.contains("word"), true);
  assert.equal(popover.childNodes[0].textContent, misspelled);
  const offers = offersOf(popover);
  assert.ok(offers.length > 0 && offers.length <= 10, `${offers.length} offers`);
  for (const button of buttonsOf(popover)) assert.equal(button.type, "button");
});

check("the popover ends with Ignore one and Ignore all, after the suggestions", () => {
  const buttons = buttonsOf(popover);
  assert.equal(ignoreOf(popover).length, 2);
  assert.equal(buttons[buttons.length - 2].textContent, "Ignore one");
  assert.equal(buttons[buttons.length - 1].textContent, "Ignore all");
  assert.equal(buttons[buttons.length - 2].classList.contains("ignore"), true);
  assert.equal(buttons[buttons.length - 1].classList.contains("ignore"), true);
});

check("the popover is pinned inside the viewport when anchoring is unavailable", () => {
  assert.equal(popover.classList.contains("anchored"), false);
  assert.equal(popover.style.props.get("left"), "300px");
  assert.equal(popover.style.props.get("top"), "434px");
});

check("choosing a suggestion edits the source, shuts the popover and re-renders", () => {
  const button = offersOf(popover)[0];
  const fix = button.textContent;
  button.fire("click");
  assert.equal(popover.showing, false);
  const written = box.tokens(source.value).map((hit) => hit.word);
  assert.ok(written.includes(fix));
  assert.ok(!written.includes(misspelled), "the token is gone, not merely the substring");
  assert.equal(written.length, box.tokens(SAMPLE).length);
  assert.equal(spans().length, 0, "nothing is underlined once the word is spelled right");
});

check("Command-Z undoes a correction on Apple devices", () => {
  const held = stage(false);
  const shown = marked(held.parts.preview);
  held.parts.preview.fire("click", { target: shown[0] });
  offersOf(held.parts.popover)[0].fire("click");
  assert.equal(held.parts.undo.disabled, false);
  assert.equal(held.parts.undo.title, "Undo last correction (⌘Z)");
  let prevented = false;
  held.box.document.fire("keydown", {
    key: "z",
    metaKey: true,
    ctrlKey: false,
    altKey: false,
    shiftKey: false,
    preventDefault: () => {
      prevented = true;
    },
  });
  assert.equal(prevented, true);
  assert.equal(held.parts.source.value, SAMPLE);
  assert.equal(held.parts.undo.disabled, true);
  assert.equal(marked(held.parts.preview).length, 1);
  assert.equal(held.parts.source.focused, true);
});

check("Ctrl-Z and the Undo button undo corrections on other devices", () => {
  const held = stage(false, undefined, "Win32");
  const correctOnce = () => {
    const shown = marked(held.parts.preview);
    held.parts.preview.fire("click", { target: shown[0] });
    offersOf(held.parts.popover)[0].fire("click");
  };
  correctOnce();
  assert.equal(held.parts.undo.title, "Undo last correction (Ctrl+Z)");
  held.box.document.fire("keydown", {
    key: "z",
    metaKey: false,
    ctrlKey: true,
    altKey: false,
    shiftKey: false,
    preventDefault() {},
  });
  assert.equal(held.parts.source.value, SAMPLE);
  correctOnce();
  held.parts.undo.fire("click");
  assert.equal(held.parts.source.value, SAMPLE);
});

check("the correction history holds more than fifty changes", () => {
  const held = stage(false, undefined, "Win32");
  const count = 60;
  const shown = marked(held.parts.preview);
  held.parts.preview.fire("click", { target: shown[0] });
  const fix = offersOf(held.parts.popover)[0].textContent;
  held.parts.source.value = Array(count).fill(misspelled).join(" ");
  held.box.render();
  for (let at = 0; at < count; at += 1) held.box.choose(misspelled, 0, fix);
  for (let at = 0; at < count; at += 1) held.parts.undo.fire("click");
  assert.equal(held.parts.source.value, Array(count).fill(misspelled).join(" "));
  assert.equal(held.parts.undo.disabled, true);
});

check("typing starts a fresh correction history", () => {
  const held = stage(false);
  const shown = marked(held.parts.preview);
  held.parts.preview.fire("click", { target: shown[0] });
  offersOf(held.parts.popover)[0].fire("click");
  assert.equal(held.parts.undo.disabled, false);
  held.parts.source.value += " typed";
  held.parts.source.fire("input", { target: held.parts.source });
  assert.equal(held.parts.undo.disabled, true);
  let prevented = false;
  held.box.document.fire("keydown", {
    key: "z",
    metaKey: true,
    ctrlKey: false,
    altKey: false,
    shiftKey: false,
    preventDefault: () => {
      prevented = true;
    },
  });
  assert.equal(prevented, false, "native text undo remains available");
});

check("the copy button writes the source and flips its label", () => {
  copyButton.fire("click");
  assert.equal(copied, source.value);
});

check("the grade toggle swaps the font class and nothing else", () => {
  const QS = vm.runInContext("QS", box);
  const listed = QS.words.slice(0, QS.words.indexOf("\n")).split("\t")[0];
  source.value = `# heading\n\n${listed} ${misspelled}\n`;
  assert.equal(grade.getAttribute("aria-pressed"), "true", "opens in Senior");

  grade.fire("click");
  box.render();
  assert.equal(grade.textContent, "Junior");
  assert.equal(preview.classList.contains("senior"), false);
  assert.equal(popover.classList.contains("senior"), false);
  assert.deepEqual(
    spans().map((span) => span.dataset.w),
    [misspelled],
    "junior face, same vocabulary",
  );

  grade.fire("click");
  box.render();
  assert.equal(grade.textContent, "Senior");
  assert.equal(preview.classList.contains("senior"), true);
  assert.equal(popover.classList.contains("senior"), true);
  assert.deepEqual(
    spans().map((span) => span.dataset.w),
    [misspelled],
    "the accepted words do not move with the face",
  );
});

check("occurrence indices count every token, code spans included", () => {
  source.value = `${misspelled} \`${misspelled}\` ${misspelled}\n`;
  box.render();
  assert.deepEqual(
    spans().map((span) => span.dataset.occ),
    ["0", "1", "2"],
    "a flat shim sees one text node, so every occurrence is numbered in order",
  );
});

check("YAML front matter never reaches the preview", () => {
  source.value = `---\ntitle: ${misspelled}\n---\n\n# heading\n\n${misspelled}\n`;
  box.render();
  assert.ok(!preview.html.includes("title:"), "the front matter block was never handed to marked");
  assert.deepEqual(
    spans().map((span) => span.dataset.occ),
    ["0"],
    "the body's occurrence is the only one the preview ever sees",
  );
});

check("an empty front matter block is stripped too", () => {
  source.value = `---\n---\n\n${misspelled}\n`;
  box.render();
  assert.equal(spans().length, 1);
  assert.ok(!preview.html.includes("<hr"), "no leftover thematic breaks from the delimiters");
});

check("anchor positioning is used where the browser has it", () => {
  const anchored = stage(true);
  assert.equal(anchored.parts.popover.classList.contains("anchored"), true);
  const shown = marked(anchored.parts.preview);
  assert.equal(shown.length, 1);
  anchored.parts.preview.fire("click", { target: shown[0] });
  assert.equal(anchored.parts.popover.showing, true);
  assert.equal(shown[0].style.props.get("anchor-name"), "--qs-miss");
  assert.equal(anchored.parts.popover.style.props.has("left"), false, "no inline placement");
  assert.equal(anchored.parts.popover.style.props.has("top"), false);
});

check("only one span carries the anchor name at a time", () => {
  const anchored = stage(true);
  anchored.parts.source.value = `${misspelled} ${misspelled}\n`;
  anchored.box.render();
  const shown = marked(anchored.parts.preview);
  assert.equal(shown.length, 2);
  anchored.parts.preview.fire("click", { target: shown[0] });
  anchored.parts.popover.showing = false;
  anchored.parts.preview.fire("click", { target: shown[1] });
  assert.equal(shown[0].style.props.has("anchor-name"), false);
  assert.equal(shown[1].style.props.get("anchor-name"), "--qs-miss");
  assert.equal(shown[0].dataset.occ, "0");
  assert.equal(shown[1].dataset.occ, "1");
});

const shelf = storage();
const excusing = stage(false, shelf);
const flagged = (held) => marked(held.parts.preview).map((span) => span.dataset.w);

function ignoreTheMisspelling(held) {
  const shown = marked(held.parts.preview);
  held.parts.preview.fire("click", { target: shown[0] });
  ignoreOf(held.parts.popover)[1].fire("click");
}

check("the button stays out of sight until something has been ignored", () => {
  assert.equal(excusing.parts.ignored.hidden, true);
  assert.deepEqual(flagged(excusing), [misspelled]);
  assert.equal(shelf.held.has(KEPT), false, "nothing is written before there is any");
});

check("ignoring a word drops its underline and writes the word down", () => {
  ignoreTheMisspelling(excusing);
  assert.equal(excusing.parts.popover.showing, false, "the popover shuts behind it");
  assert.deepEqual(flagged(excusing), []);
  assert.equal(excusing.parts.ignored.hidden, false);
  assert.equal(excusing.parts.ignored.textContent, "Unignore 1");
  assert.deepEqual(JSON.parse(shelf.held.get(KEPT)), [misspelled]);
});

check("a page opened again over the same storage starts out knowing", () => {
  const again = stage(false, shelf);
  assert.deepEqual(flagged(again), []);
  assert.equal(again.parts.ignored.hidden, false);
  assert.equal(again.parts.ignored.textContent, "Unignore 1");
});

check("the button clears the list, the storage and the underline it was hiding", () => {
  excusing.parts.ignored.fire("click");
  assert.equal(excusing.parts.ignored.hidden, true);
  assert.deepEqual(JSON.parse(shelf.held.get(KEPT)), []);
  assert.deepEqual(flagged(excusing), [misspelled]);
  assert.deepEqual(flagged(stage(false, shelf)), [misspelled]);
});

check("an origin whose storage throws still ignores for the session", () => {
  const sessional = stage(false, sealed);
  assert.deepEqual(flagged(sessional), [misspelled]);
  ignoreTheMisspelling(sessional);
  assert.deepEqual(flagged(sessional), []);
  assert.equal(sessional.parts.ignored.textContent, "Unignore 1");
});

const briefly = storage();
const passing = stage(false, briefly);

function ignoreOneOccurrence(held, at) {
  const shown = marked(held.parts.preview);
  held.parts.preview.fire("click", { target: shown[at] });
  ignoreOf(held.parts.popover)[0].fire("click");
}

check("ignoring one occurrence leaves the other underlined and writes nothing", () => {
  passing.parts.source.value = `${misspelled} ${misspelled}\n`;
  passing.box.render();
  assert.equal(marked(passing.parts.preview).length, 2);
  ignoreOneOccurrence(passing, 0);
  const shown = marked(passing.parts.preview);
  assert.equal(shown.length, 1);
  assert.equal(shown[0].dataset.occ, "1", "the second occurrence is the one still flagged");
  assert.equal(passing.parts.ignored.hidden, false);
  assert.equal(passing.parts.ignored.textContent, "Unignore 1");
  assert.equal(briefly.held.has(KEPT), false, "an occurrence ignore is session-only");
});

check("the button clears occurrence ignores too", () => {
  passing.parts.ignored.fire("click");
  assert.equal(passing.parts.ignored.hidden, true);
  assert.equal(marked(passing.parts.preview).length, 2);
});

check("ignoring the word everywhere absorbs its occurrence ignores", () => {
  ignoreOneOccurrence(passing, 0);
  ignoreTheMisspelling(passing);
  assert.deepEqual(flagged(passing), []);
  assert.equal(passing.parts.ignored.textContent, "Unignore 1");
  assert.deepEqual(JSON.parse(briefly.held.get(KEPT)), [misspelled]);
});

const sweeping = stage(false);

check("every suggestion row carries a correct-all option counting the others", () => {
  sweeping.parts.source.value = `${misspelled} ${misspelled} ${misspelled}\n`;
  sweeping.box.render();
  const shown = marked(sweeping.parts.preview);
  assert.equal(shown.length, 3);
  sweeping.parts.preview.fire("click", { target: shown[0] });
  const offers = offersOf(sweeping.parts.popover);
  const sweepers = sweepersOf(sweeping.parts.popover);
  assert.ok(offers.length > 0);
  assert.equal(sweepers.length, offers.length);
  for (const [at, held] of sweepers.entries()) {
    assert.equal(held.type, "button");
    assert.equal(held.textContent, "(2)");
    assert.ok(held.parentNode.classList.contains("suggestion"));
    assert.equal(held.parentNode, offers[at].parentNode, "each pair shares a row");
    assert.ok(held.title.includes("2 others"), held.title);
  }
  const [once, leave] = ignoreOf(sweeping.parts.popover);
  assert.equal(leave.textContent, "Ignore all (2)");
  assert.ok(leave.title.length > 0);
  assert.ok(once.title.length > 0);
});

check("the correct-all option rewrites every occurrence at once", () => {
  const fix = offersOf(sweeping.parts.popover)[0].textContent;
  sweepersOf(sweeping.parts.popover)[0].fire("click");
  assert.equal(sweeping.parts.popover.showing, false);
  const written = sweeping.box.tokens(sweeping.parts.source.value).map((hit) => hit.word);
  assert.deepEqual(written, sweeping.box.tokens(`${fix} ${fix} ${fix}`).map((hit) => hit.word));
  assert.equal(marked(sweeping.parts.preview).length, 0);
});

check("a lone misspelling gets no correct-all option and a plain Ignore all", () => {
  const alone = stage(false);
  const shown = marked(alone.parts.preview);
  assert.equal(shown.length, 1);
  alone.parts.preview.fire("click", { target: shown[0] });
  assert.ok(offersOf(alone.parts.popover).length > 0);
  assert.equal(sweepersOf(alone.parts.popover).length, 0);
  assert.equal(ignoreOf(alone.parts.popover)[1].textContent, "Ignore all");
});

check("an occurrence ignored by hand is left out of the sweep", () => {
  const sparing = stage(false);
  sparing.parts.source.value = `${misspelled} ${misspelled} ${misspelled}\n`;
  sparing.box.render();
  ignoreOneOccurrence(sparing, 1);
  const shown = marked(sparing.parts.preview);
  assert.equal(shown.length, 2);
  sparing.parts.preview.fire("click", { target: shown[0] });
  assert.equal(sweepersOf(sparing.parts.popover)[0].textContent, "(1)");
  assert.ok(sweepersOf(sparing.parts.popover)[0].title.includes("1 other"), "singular title");
  const fix = offersOf(sparing.parts.popover)[0].textContent;
  sweepersOf(sparing.parts.popover)[0].fire("click");
  const written = sparing.box.tokens(sparing.parts.source.value).map((hit) => hit.word);
  assert.deepEqual(
    written,
    sparing.box.tokens(`${fix} ${misspelled} ${fix}`).map((hit) => hit.word),
    "the excused occurrence keeps its spelling",
  );
  assert.equal(marked(sparing.parts.preview).length, 0, "and stays excused renumbered");
});

const dressed = storage();
const graded = stage(false, dressed);

check("a grade choice is written down when the toggle moves", () => {
  assert.equal(graded.parts.grade.getAttribute("aria-pressed"), "true", "opens in Senior");
  graded.parts.grade.fire("click");
  assert.equal(dressed.held.get(CHOSEN), "junior");
  graded.parts.grade.fire("click");
  assert.equal(dressed.held.get(CHOSEN), "senior");
});

check("a page opened again over the same storage starts in the grade it left", () => {
  const again = stage(false, dressed);
  assert.equal(again.parts.grade.getAttribute("aria-pressed"), "true");
  assert.equal(again.parts.preview.classList.contains("senior"), true);
});

check("an origin whose storage throws still switches grade for the session", () => {
  const sessional = stage(false, sealed);
  assert.equal(sessional.parts.grade.getAttribute("aria-pressed"), "true");
  sessional.parts.grade.fire("click");
  assert.equal(sessional.parts.preview.classList.contains("senior"), false);
});

const typed = stage(false);
const RESTING = typed.parts.preview.html;
typed.parts.source.value = `# typed\n\n${misspelled}\n`;
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
      [misspelled],
    );
  });
  for (const each of done) console.log(`ok    ${each}`);
  console.log(`\n${done.length} checks passed`);
}, 300);
