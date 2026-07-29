const TOKEN = /[\uE650-\uE67E][\uE650-\uE67E-]*/g;
const HYPHEN = "-";
const SPACE = " ";
const OFFERS = 8;
const FRONT_MATTER = /^---\r?\n(?:[\s\S]*?\r?\n)?---[ \t]*\r?\n?/;

function stripFrontMatter(text) {
  return text.replace(FRONT_MATTER, "");
}

function tokens(text) {
  const found = [];
  TOKEN.lastIndex = 0;
  for (let match = TOKEN.exec(text); match !== null; match = TOKEN.exec(text)) {
    found.push({ word: match[0], start: match.index, end: TOKEN.lastIndex });
  }
  return found;
}

function accepts(active, word) {
  if (active.has(word)) return true;
  if (!word.includes(HYPHEN)) return false;
  return word.split(HYPHEN).every((piece) => piece === "" || active.has(piece));
}

function offered(active, candidate) {
  return candidate.split(SPACE).every((piece) => accepts(active, piece));
}

function frequency(counts, word) {
  const counted = typeof counts.get === "function" ? counts.get(word) : counts[word];
  return counted || 0;
}

function ranked(candidates, score) {
  return candidates
    .map((candidate, order) => ({ candidate, order, score: score(candidate) }))
    .sort((one, other) => other.score - one.score || one.order - other.order)
    .map((entry) => entry.candidate);
}

function bridged(word, rep) {
  const out = [];
  for (const [written, meant] of rep) {
    for (let at = word.indexOf(written); at >= 0; at = word.indexOf(written, at + 1)) {
      out.push(word.slice(0, at) + meant + word.slice(at + written.length));
    }
  }
  return out;
}

function nearby(word, letters) {
  const out = [];
  for (let i = 0; i < word.length; i += 1) {
    out.push(word.slice(0, i) + word.slice(i + 1));
  }
  for (let i = 0; i + 1 < word.length; i += 1) {
    out.push(word.slice(0, i) + word[i + 1] + word[i] + word.slice(i + 2));
  }
  for (const letter of letters) {
    for (let i = 0; i < word.length; i += 1) {
      if (word[i] !== letter) out.push(word.slice(0, i) + letter + word.slice(i + 1));
    }
  }
  for (const letter of letters) {
    for (let i = 0; i <= word.length; i += 1) {
      out.push(word.slice(0, i) + letter + word.slice(i));
    }
  }
  return out;
}

function halves(word) {
  const out = [];
  for (let i = 1; i < word.length; i += 1) {
    out.push([word.slice(0, i), word.slice(i)]);
  }
  return out;
}

function suggest(word, ctx) {
  const active = ctx.active;
  const counts = ctx.freq;
  const limit = ctx.limit || OFFERS;
  const out = [];
  const seen = new Set([word]);
  const take = (candidates) => {
    for (const candidate of candidates) {
      if (out.length >= limit) return;
      if (seen.has(candidate) || !offered(active, candidate)) continue;
      seen.add(candidate);
      out.push(candidate);
    }
  };

  take(bridged(word, ctx.rep));
  take(
    ranked(
      nearby(word, ctx.letters).filter((candidate) => offered(active, candidate)),
      (candidate) => frequency(counts, candidate),
    ),
  );
  take(
    ranked(
      halves(word).filter((pair) => accepts(active, pair[0]) && accepts(active, pair[1])),
      (pair) => Math.min(frequency(counts, pair[0]), frequency(counts, pair[1])),
    ).map((pair) => pair.join(SPACE)),
  );
  return out;
}

function replaceOccurrence(source, word, occurrence, replacement) {
  const written = tokens(source).filter((hit) => hit.word === word);
  if (written.length === 0) return source;
  const hit = written[occurrence] || written[0];
  return source.slice(0, hit.start) + replacement + source.slice(hit.end);
}

if (typeof module !== "undefined") {
  module.exports = { TOKEN, tokens, accepts, suggest, replaceOccurrence, stripFrontMatter };
}
