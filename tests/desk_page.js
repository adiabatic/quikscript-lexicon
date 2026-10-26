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
  const names = new Set();
  return {
    names,
    add: (name) => names.add(name),
    remove: (name) => names.delete(name),
    contains: (name) => names.has(name),
    toggle: (name, on) => (on ? names.add(name) : names.delete(name)),
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
    return [...this.classList.names].join(" ");
  }

  set className(value) {
    this.classList.names.clear();
    for (const name of value.split(" ")) if (name) this.classList.names.add(name);
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
    for (let node = this; node; node = node.parentNode) {
      if (node.nodeType === 1 && node.matches(selector)) return node;
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
    assert.equal(this.showing, true, "hidePopover on a closed popover would throw");
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

function withFlatInnerHTML(element) {
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

const IGNORED_STORAGE_KEY = "qs-desk.ignored";
const GRADE_STORAGE_KEY = "qs-desk.senior";

function storage() {
  const items = new Map();
  return {
    items,
    getItem: (key) => (items.has(key) ? items.get(key) : null),
    setItem: (key, value) => items.set(key, String(value)),
  };
}

const throwingStorage = {
  getItem() {
    throw new Error("this origin has no storage");
  },
  setItem() {
    throw new Error("this origin has no storage");
  },
};

function loadPage(supports, pageStorage, platform = "MacIntel") {
  const parts = {
    source: new Element("textarea"),
    preview: withFlatInnerHTML(new Element("div")),
    grade: new Element("button"),
    popover: new Element("div"),
    copy: new Element("button"),
    undo: new Element("button"),
    unignore: new Element("button"),
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
    localStorage: pageStorage || storage(),
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

const { parts, box } = loadPage(false);
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

check("the first render underlines the one word the lexicon does not list", () => {
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
      : (node.childNodes || []).filter((child) => child.tagName === "BUTTON"),
  );
const suggestionsOf = (element) =>
  buttonsOf(element).filter(
    (node) => !node.classList.contains("ignore") && !node.classList.contains("fix-all"),
  );
const fixAllButtonsOf = (element) =>
  buttonsOf(element).filter((node) => node.classList.contains("fix-all"));
const ignoreOf = (element) =>
  buttonsOf(element).filter((node) => node.classList.contains("ignore"));

check("clicking the underline opens the popover with suggestions", () => {
  preview.fire("click", { target: spans()[0] });
  assert.equal(popover.showing, true);
  assert.equal(popover.childNodes[0].tagName, "DIV");
  assert.equal(popover.childNodes[0].classList.contains("word"), true);
  assert.equal(popover.childNodes[0].textContent, misspelled);
  const suggestions = suggestionsOf(popover);
  assert.ok(
    suggestions.length > 0 && suggestions.length <= 10,
    `${suggestions.length} suggestions`,
  );
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

check("the popover is placed with left and top when anchor positioning is unavailable", () => {
  assert.equal(popover.classList.contains("anchored"), false);
  assert.equal(popover.style.props.get("left"), "300px");
  assert.equal(popover.style.props.get("top"), "434px");
});

check("choosing a suggestion edits the source, closes the popover and re-renders", () => {
  const button = suggestionsOf(popover)[0];
  const suggestion = button.textContent;
  button.fire("click");
  assert.equal(popover.showing, false);
  const written = box.tokens(source.value).map((hit) => hit.word);
  assert.ok(written.includes(suggestion));
  assert.ok(!written.includes(misspelled), "the token is gone, not merely the substring");
  assert.equal(written.length, box.tokens(SAMPLE).length);
  assert.equal(spans().length, 0, "nothing is underlined once the word is spelled right");
});

check("Command-Z undoes a correction on Apple devices", () => {
  const loadedPage = loadPage(false);
  const shown = marked(loadedPage.parts.preview);
  loadedPage.parts.preview.fire("click", { target: shown[0] });
  suggestionsOf(loadedPage.parts.popover)[0].fire("click");
  assert.equal(loadedPage.parts.undo.disabled, false);
  assert.equal(loadedPage.parts.undo.title, "Undo last correction (⌘Z)");
  let prevented = false;
  loadedPage.box.document.fire("keydown", {
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
  assert.equal(loadedPage.parts.source.value, SAMPLE);
  assert.equal(loadedPage.parts.undo.disabled, true);
  assert.equal(marked(loadedPage.parts.preview).length, 1);
  assert.equal(loadedPage.parts.source.focused, true);
});

check("Ctrl-Z and the Undo button undo corrections on other devices", () => {
  const loadedPage = loadPage(false, undefined, "Win32");
  const correctOnce = () => {
    const shown = marked(loadedPage.parts.preview);
    loadedPage.parts.preview.fire("click", { target: shown[0] });
    suggestionsOf(loadedPage.parts.popover)[0].fire("click");
  };
  correctOnce();
  assert.equal(loadedPage.parts.undo.title, "Undo last correction (Ctrl+Z)");
  loadedPage.box.document.fire("keydown", {
    key: "z",
    metaKey: false,
    ctrlKey: true,
    altKey: false,
    shiftKey: false,
    preventDefault() {},
  });
  assert.equal(loadedPage.parts.source.value, SAMPLE);
  correctOnce();
  loadedPage.parts.undo.fire("click");
  assert.equal(loadedPage.parts.source.value, SAMPLE);
});

check("the correction history holds more than fifty changes", () => {
  const loadedPage = loadPage(false, undefined, "Win32");
  const count = 60;
  const shown = marked(loadedPage.parts.preview);
  loadedPage.parts.preview.fire("click", { target: shown[0] });
  const suggestion = suggestionsOf(loadedPage.parts.popover)[0].textContent;
  loadedPage.parts.source.value = Array(count).fill(misspelled).join(" ");
  loadedPage.box.render();
  for (let at = 0; at < count; at += 1) loadedPage.box.choose(misspelled, 0, suggestion);
  for (let at = 0; at < count; at += 1) loadedPage.parts.undo.fire("click");
  assert.equal(loadedPage.parts.source.value, Array(count).fill(misspelled).join(" "));
  assert.equal(loadedPage.parts.undo.disabled, true);
});

check("typing starts a fresh correction history", () => {
  const loadedPage = loadPage(false);
  const shown = marked(loadedPage.parts.preview);
  loadedPage.parts.preview.fire("click", { target: shown[0] });
  suggestionsOf(loadedPage.parts.popover)[0].fire("click");
  assert.equal(loadedPage.parts.undo.disabled, false);
  loadedPage.parts.source.value += " typed";
  loadedPage.parts.source.fire("input", { target: loadedPage.parts.source });
  assert.equal(loadedPage.parts.undo.disabled, true);
  let prevented = false;
  loadedPage.box.document.fire("keydown", {
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

check("the copy button copies the source to the clipboard", () => {
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
    "the accepted words do not change with the font face",
  );
});

check("occurrence indices count every token, code spans included", () => {
  source.value = `${misspelled} \`${misspelled}\` ${misspelled}\n`;
  box.render();
  assert.deepEqual(
    spans().map((span) => span.dataset.occ),
    ["0", "1", "2"],
    "withFlatInnerHTML puts the preview in one text node, so every occurrence is flagged and numbered in order",
  );
});

check("YAML front matter is not rendered in the preview", () => {
  source.value = `---\ntitle: ${misspelled}\n---\n\n# heading\n\n${misspelled}\n`;
  box.render();
  assert.ok(!preview.html.includes("title:"), "the front matter block is not in the preview HTML");
  assert.deepEqual(
    spans().map((span) => span.dataset.occ),
    ["0"],
    "the body's occurrence is the only one in the preview, so it is numbered 0",
  );
});

check("an empty front matter block is stripped too", () => {
  source.value = `---\n---\n\n${misspelled}\n`;
  box.render();
  assert.equal(spans().length, 1);
  assert.ok(!preview.html.includes("<hr"), "no leftover thematic breaks from the delimiters");
});

check("anchor positioning is used where the browser has it", () => {
  const anchorPage = loadPage(true);
  assert.equal(anchorPage.parts.popover.classList.contains("anchored"), true);
  const shown = marked(anchorPage.parts.preview);
  assert.equal(shown.length, 1);
  anchorPage.parts.preview.fire("click", { target: shown[0] });
  assert.equal(anchorPage.parts.popover.showing, true);
  assert.equal(shown[0].style.props.get("anchor-name"), "--qs-miss");
  assert.equal(anchorPage.parts.popover.style.props.has("left"), false, "no inline placement");
  assert.equal(anchorPage.parts.popover.style.props.has("top"), false);
});

check("only one span has the anchor name at a time", () => {
  const anchorPage = loadPage(true);
  anchorPage.parts.source.value = `${misspelled} ${misspelled}\n`;
  anchorPage.box.render();
  const shown = marked(anchorPage.parts.preview);
  assert.equal(shown.length, 2);
  anchorPage.parts.preview.fire("click", { target: shown[0] });
  anchorPage.parts.popover.showing = false;
  anchorPage.parts.preview.fire("click", { target: shown[1] });
  assert.equal(shown[0].style.props.has("anchor-name"), false);
  assert.equal(shown[1].style.props.get("anchor-name"), "--qs-miss");
  assert.equal(shown[0].dataset.occ, "0");
  assert.equal(shown[1].dataset.occ, "1");
});

const ignoreStorage = storage();
const ignoreAllPage = loadPage(false, ignoreStorage);
const flagged = (loadedPage) => marked(loadedPage.parts.preview).map((span) => span.dataset.w);

function ignoreTheMisspelling(loadedPage) {
  const shown = marked(loadedPage.parts.preview);
  loadedPage.parts.preview.fire("click", { target: shown[0] });
  ignoreOf(loadedPage.parts.popover)[1].fire("click");
}

check("the unignore button is hidden until something has been ignored", () => {
  assert.equal(ignoreAllPage.parts.unignore.hidden, true);
  assert.deepEqual(flagged(ignoreAllPage), [misspelled]);
  assert.equal(
    ignoreStorage.items.has(IGNORED_STORAGE_KEY),
    false,
    "nothing is saved before a word is ignored",
  );
});

check("ignoring a word removes its underline and saves the word to storage", () => {
  ignoreTheMisspelling(ignoreAllPage);
  assert.equal(ignoreAllPage.parts.popover.showing, false, "the popover closes");
  assert.deepEqual(flagged(ignoreAllPage), []);
  assert.equal(ignoreAllPage.parts.unignore.hidden, false);
  assert.equal(ignoreAllPage.parts.unignore.textContent, "Unignore 1");
  assert.deepEqual(JSON.parse(ignoreStorage.items.get(IGNORED_STORAGE_KEY)), [misspelled]);
});

check("a reloaded page restores ignored words from storage", () => {
  const reloadedPage = loadPage(false, ignoreStorage);
  assert.deepEqual(flagged(reloadedPage), []);
  assert.equal(reloadedPage.parts.unignore.hidden, false);
  assert.equal(reloadedPage.parts.unignore.textContent, "Unignore 1");
});

check("the unignore button clears the list and the storage and restores the underline", () => {
  ignoreAllPage.parts.unignore.fire("click");
  assert.equal(ignoreAllPage.parts.unignore.hidden, true);
  assert.deepEqual(JSON.parse(ignoreStorage.items.get(IGNORED_STORAGE_KEY)), []);
  assert.deepEqual(flagged(ignoreAllPage), [misspelled]);
  assert.deepEqual(flagged(loadPage(false, ignoreStorage)), [misspelled]);
});

check("an origin whose storage throws still ignores for the session", () => {
  const noStoragePage = loadPage(false, throwingStorage);
  assert.deepEqual(flagged(noStoragePage), [misspelled]);
  ignoreTheMisspelling(noStoragePage);
  assert.deepEqual(flagged(noStoragePage), []);
  assert.equal(noStoragePage.parts.unignore.textContent, "Unignore 1");
});

const occurrenceStorage = storage();
const occurrencePage = loadPage(false, occurrenceStorage);

function ignoreOneOccurrence(loadedPage, at) {
  const shown = marked(loadedPage.parts.preview);
  loadedPage.parts.preview.fire("click", { target: shown[at] });
  ignoreOf(loadedPage.parts.popover)[0].fire("click");
}

check("ignoring one occurrence leaves the other underlined and saves nothing to storage", () => {
  occurrencePage.parts.source.value = `${misspelled} ${misspelled}\n`;
  occurrencePage.box.render();
  assert.equal(marked(occurrencePage.parts.preview).length, 2);
  ignoreOneOccurrence(occurrencePage, 0);
  const shown = marked(occurrencePage.parts.preview);
  assert.equal(shown.length, 1);
  assert.equal(shown[0].dataset.occ, "1", "the second occurrence is the one still flagged");
  assert.equal(occurrencePage.parts.unignore.hidden, false);
  assert.equal(occurrencePage.parts.unignore.textContent, "Unignore 1");
  assert.equal(
    occurrenceStorage.items.has(IGNORED_STORAGE_KEY),
    false,
    "an occurrence ignore is session-only",
  );
});

check("the button clears occurrence ignores too", () => {
  occurrencePage.parts.unignore.fire("click");
  assert.equal(occurrencePage.parts.unignore.hidden, true);
  assert.equal(marked(occurrencePage.parts.preview).length, 2);
});

check("ignoring the word everywhere replaces its occurrence ignores", () => {
  ignoreOneOccurrence(occurrencePage, 0);
  ignoreTheMisspelling(occurrencePage);
  assert.deepEqual(flagged(occurrencePage), []);
  assert.equal(occurrencePage.parts.unignore.textContent, "Unignore 1");
  assert.deepEqual(JSON.parse(occurrenceStorage.items.get(IGNORED_STORAGE_KEY)), [misspelled]);
});

const fixAllPage = loadPage(false);

check("every suggestion row has a fix-all option with the count of other occurrences", () => {
  fixAllPage.parts.source.value = `${misspelled} ${misspelled} ${misspelled}\n`;
  fixAllPage.box.render();
  const shown = marked(fixAllPage.parts.preview);
  assert.equal(shown.length, 3);
  fixAllPage.parts.preview.fire("click", { target: shown[0] });
  const suggestions = suggestionsOf(fixAllPage.parts.popover);
  const fixAllButtons = fixAllButtonsOf(fixAllPage.parts.popover);
  assert.ok(suggestions.length > 0);
  assert.equal(fixAllButtons.length, suggestions.length);
  for (const [at, button] of fixAllButtons.entries()) {
    assert.equal(button.type, "button");
    assert.equal(button.textContent, "(2)");
    assert.ok(button.parentNode.classList.contains("suggestion"));
    assert.equal(button.parentNode, suggestions[at].parentNode, "each pair shares a row");
    assert.ok(button.title.includes("2 others"), button.title);
  }
  const [ignoreOne, ignoreAll] = ignoreOf(fixAllPage.parts.popover);
  assert.equal(ignoreAll.textContent, "Ignore all (2)");
  assert.ok(ignoreAll.title.length > 0);
  assert.ok(ignoreOne.title.length > 0);
});

check("the fix-all option rewrites every occurrence at once", () => {
  const suggestion = suggestionsOf(fixAllPage.parts.popover)[0].textContent;
  fixAllButtonsOf(fixAllPage.parts.popover)[0].fire("click");
  assert.equal(fixAllPage.parts.popover.showing, false);
  const written = fixAllPage.box.tokens(fixAllPage.parts.source.value).map((hit) => hit.word);
  assert.deepEqual(
    written,
    fixAllPage.box.tokens(`${suggestion} ${suggestion} ${suggestion}`).map((hit) => hit.word),
  );
  assert.equal(marked(fixAllPage.parts.preview).length, 0);
});

check("a lone misspelling gets no fix-all option and a plain Ignore all", () => {
  const lonePage = loadPage(false);
  const shown = marked(lonePage.parts.preview);
  assert.equal(shown.length, 1);
  lonePage.parts.preview.fire("click", { target: shown[0] });
  assert.ok(suggestionsOf(lonePage.parts.popover).length > 0);
  assert.equal(fixAllButtonsOf(lonePage.parts.popover).length, 0);
  assert.equal(ignoreOf(lonePage.parts.popover)[1].textContent, "Ignore all");
});

check("fix all skips an occurrence the user ignored", () => {
  const fixAllSkipPage = loadPage(false);
  fixAllSkipPage.parts.source.value = `${misspelled} ${misspelled} ${misspelled}\n`;
  fixAllSkipPage.box.render();
  ignoreOneOccurrence(fixAllSkipPage, 1);
  const shown = marked(fixAllSkipPage.parts.preview);
  assert.equal(shown.length, 2);
  fixAllSkipPage.parts.preview.fire("click", { target: shown[0] });
  assert.equal(fixAllButtonsOf(fixAllSkipPage.parts.popover)[0].textContent, "(1)");
  assert.ok(
    fixAllButtonsOf(fixAllSkipPage.parts.popover)[0].title.includes("1 other"),
    "singular title",
  );
  const suggestion = suggestionsOf(fixAllSkipPage.parts.popover)[0].textContent;
  fixAllButtonsOf(fixAllSkipPage.parts.popover)[0].fire("click");
  const written = fixAllSkipPage.box
    .tokens(fixAllSkipPage.parts.source.value)
    .map((hit) => hit.word);
  assert.deepEqual(
    written,
    fixAllSkipPage.box.tokens(`${suggestion} ${misspelled} ${suggestion}`).map((hit) => hit.word),
    "the ignored occurrence keeps its spelling",
  );
  assert.equal(
    marked(fixAllSkipPage.parts.preview).length,
    0,
    "and stays ignored after renumbering",
  );
});

const gradeStorage = storage();
const gradePage = loadPage(false, gradeStorage);

check("a grade choice is saved to storage when the toggle is clicked", () => {
  assert.equal(gradePage.parts.grade.getAttribute("aria-pressed"), "true", "opens in Senior");
  gradePage.parts.grade.fire("click");
  assert.equal(gradeStorage.items.get(GRADE_STORAGE_KEY), "junior");
  gradePage.parts.grade.fire("click");
  assert.equal(gradeStorage.items.get(GRADE_STORAGE_KEY), "senior");
});

check("a reloaded page restores the grade from storage", () => {
  const reloadedPage = loadPage(false, gradeStorage);
  assert.equal(reloadedPage.parts.grade.getAttribute("aria-pressed"), "true");
  assert.equal(reloadedPage.parts.preview.classList.contains("senior"), true);
});

check("an origin whose storage throws still switches grade for the session", () => {
  const noStoragePage = loadPage(false, throwingStorage);
  assert.equal(noStoragePage.parts.grade.getAttribute("aria-pressed"), "true");
  noStoragePage.parts.grade.fire("click");
  assert.equal(noStoragePage.parts.preview.classList.contains("senior"), false);
});

const typed = loadPage(false);
const HTML_BEFORE_TYPING = typed.parts.preview.html;
typed.parts.source.value = `# typed\n\n${misspelled}\n`;
typed.parts.source.fire("input", { target: typed.parts.source });

check("typing does not re-render before the debounce has elapsed", () => {
  assert.equal(typed.parts.preview.html, HTML_BEFORE_TYPING);
});

setTimeout(() => {
  check("the debounced render runs once it has", () => {
    assert.notEqual(typed.parts.preview.html, HTML_BEFORE_TYPING);
    assert.ok(typed.parts.preview.html.includes("typed"));
    assert.deepEqual(
      marked(typed.parts.preview).map((span) => span.dataset.w),
      [misspelled],
    );
  });
  for (const each of done) console.log(`ok    ${each}`);
  console.log(`\n${done.length} checks passed`);
}, 300);
