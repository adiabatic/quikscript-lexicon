const TOKEN =
  /[\uE650-\uE66C\uE670-\uE67E](?:[\p{Cf}\uFE00-\uFE0F]*[\uE650-\uE66C\uE670-\uE67E-])*/gu;
const INVISIBLE = /[\p{Cf}\uFE00-\uFE0F]/u;
const HYPHEN = "-";
const NAMER = "·";
const SPACE = " ";
const OFFERS = 10;
const DISTANT = 3;
const FRONT_MATTER = /^---\r?\n(?:[\s\S]*?\r?\n)?---[ \t]*\r?\n?/;

function stripFrontMatter(text) {
  return text.replace(FRONT_MATTER, "");
}

function named(text, at) {
  let back = at - 1;
  while (back >= 0 && INVISIBLE.test(text[back])) back -= 1;
  return text[back] === NAMER;
}

function tokens(text) {
  const found = [];
  TOKEN.lastIndex = 0;
  for (let match = TOKEN.exec(text); match !== null; match = TOKEN.exec(text)) {
    const word = match[0].split(INVISIBLE).join("");
    if (word.length === 1 && named(text, match.index)) continue;
    found.push({ word, start: match.index, end: TOKEN.lastIndex });
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

function confused(word, groups) {
  const out = [];
  for (const group of groups) {
    for (let i = 0; i < word.length; i += 1) {
      if (!group.includes(word[i])) continue;
      for (const letter of group) {
        if (letter !== word[i]) out.push(word.slice(0, i) + letter + word.slice(i + 1));
      }
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

function distance(a, b, cap) {
  if (Math.abs(a.length - b.length) > cap) return cap + 1;
  let previous2 = null;
  let previous1 = Array.from({ length: b.length + 1 }, (_, j) => j);
  for (let i = 1; i <= a.length; i += 1) {
    const current = [i];
    let least = i;
    for (let j = 1; j <= b.length; j += 1) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      let best = Math.min(previous1[j] + 1, current[j - 1] + 1, previous1[j - 1] + cost);
      if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) {
        best = Math.min(best, previous2[j - 2] + 1);
      }
      current[j] = best;
      if (best < least) least = best;
    }
    if (least > cap) return cap + 1;
    previous2 = previous1;
    previous1 = current;
  }
  return previous1[b.length];
}

function distant(word, active, cap) {
  const out = [];
  for (const candidate of active) {
    if (candidate === word) continue;
    const edits = distance(word, candidate, cap);
    if (edits <= cap) out.push({ candidate, edits });
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
      confused(word, ctx.groups).filter((candidate) => offered(active, candidate)),
      (candidate) => frequency(counts, candidate),
    ),
  );
  take(
    ranked(
      nearby(word, ctx.letters).filter((candidate) => offered(active, candidate)),
      (candidate) => frequency(counts, candidate),
    ),
  );
  const far = distant(word, active, DISTANT);
  for (let edits = 1; edits <= DISTANT; edits += 1) {
    take(
      ranked(
        far.filter((hit) => hit.edits === edits).map((hit) => hit.candidate),
        (candidate) => frequency(counts, candidate),
      ),
    );
  }
  take(
    ranked(
      halves(word).filter((pair) => accepts(active, pair[0]) && accepts(active, pair[1])),
      (pair) => Math.min(frequency(counts, pair[0]), frequency(counts, pair[1])),
    ).map((pair) => pair.join(SPACE)),
  );
  return out;
}

function replaceOccurrences(source, word, occurrences, replacement) {
  const lead = source.length - stripFrontMatter(source).length;
  const written = tokens(source.slice(lead)).filter((hit) => hit.word === word);
  if (written.length === 0) return source;
  const chosen = [...new Set(occurrences)]
    .filter((occurrence) => written[occurrence])
    .sort((one, other) => one - other);
  const hits = chosen.length ? chosen.map((occurrence) => written[occurrence]) : [written[0]];
  let out = "";
  let at = 0;
  for (const hit of hits) {
    out += source.slice(at, lead + hit.start) + replacement;
    at = lead + hit.end;
  }
  return out + source.slice(at);
}

function replaceOccurrence(source, word, occurrence, replacement) {
  return replaceOccurrences(source, word, [occurrence], replacement);
}

if (typeof module !== "undefined") {
  module.exports = {
    TOKEN,
    tokens,
    accepts,
    distance,
    suggest,
    replaceOccurrence,
    replaceOccurrences,
    stripFrontMatter,
  };
}
