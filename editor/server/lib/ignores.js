const { appendFileSync, mkdirSync, readFileSync, statSync } = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const IGNORE = ".quikscript-ignore";
const BREAK = /\r\n|\r|\n/;

/**
 * @param {NodeJS.ProcessEnv} env
 * @returns {string}
 */
function userIgnorePath(env) {
  const base = env.XDG_CONFIG_HOME || path.join(os.homedir(), ".config");
  return path.join(base, "quikscript", "ignore");
}

/**
 * @param {string} directory
 * @returns {string}
 */
function projectIgnorePath(directory) {
  return path.join(directory, IGNORE);
}

/**
 * @param {string} directory
 * @returns {string[]}
 */
function above(directory) {
  const out = [];
  let at = path.resolve(directory);
  for (;;) {
    out.push(projectIgnorePath(at));
    const up = path.dirname(at);
    if (up === at) return out;
    at = up;
  }
}

/**
 * @param {string} text
 * @returns {Set<string>}
 */
function parsed(text) {
  const words = new Set();
  for (const line of text.split(BREAK)) {
    const word = line.trim();
    if (word) words.add(word);
  }
  return words;
}

function ledger() {
  /** @type {Map<string, {stamped: number, words: Set<string>}>} */
  const held = new Map();
  return {
    /**
     * @param {string[]} paths
     * @returns {Set<string>}
     */
    read(paths) {
      const union = new Set();
      for (const file of paths) {
        let stamped;
        try {
          stamped = statSync(file).mtimeMs;
        } catch {
          held.delete(file);
          continue;
        }
        let entry = held.get(file);
        if (!entry || entry.stamped !== stamped) {
          let words;
          try {
            words = parsed(readFileSync(file, "utf8"));
          } catch {
            words = new Set();
          }
          entry = { stamped, words };
          held.set(file, entry);
        }
        for (const word of entry.words) union.add(word);
      }
      return union;
    },
    /**
     * @param {string} file
     * @param {string} word
     */
    append(file, word) {
      let text;
      try {
        text = readFileSync(file, "utf8");
      } catch {
        text = null;
      }
      if (text !== null && parsed(text).has(word)) return;
      if (text === null) mkdirSync(path.dirname(file), { recursive: true });
      const seam = text === null || text === "" || text.endsWith("\n") ? "" : "\n";
      appendFileSync(file, `${seam}${word}\n`);
      held.delete(file);
    },
  };
}

module.exports = { above, ledger, projectIgnorePath, userIgnorePath };
