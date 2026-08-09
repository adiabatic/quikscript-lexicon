"""The Quikscript Desk page, projected from the lexicon like every artifact.

site/index.html is generated, never hand-edited: the word set it checks against, the suggestion tables it offers, the fonts it renders in and the Markdown parser it runs are all inlined here from the committed master and the pinned vendored assets. That makes the page a single file that works from a file: URL with no request to anywhere, and it makes a page that disagrees with lexicon/ a freshness failure rather than a discovery.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import re
import sys
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from qslex.build import ARTIFACTS, HUNSPELL_AFF, HUNSPELL_DIC, LEXICON_JSON
from qslex.csur import CODEPOINT_OF
from qslex.hunspell import X_LETTERS, by_frequency, spellings
from qslex.letters import VOWELS, parse, render_qs
from qslex.readlex import repo_root
from qslex.words import Contraction, load_contractions

SITE = "site"
PAGE = "index.html"

WEB = Path(__file__).resolve().parent / "web"
TEMPLATE = "template.html"
STYLESHEET = "app.css"
CORE = "core.js"
APP = "app.js"

WORD_ROW = "word"

FONTS = {
    "SANS_JUNIOR_REGULAR": "AbbotsMortonSpaceportSansJunior-Regular.woff2",
    "SANS_JUNIOR_BOLD": "AbbotsMortonSpaceportSansJunior-Bold.woff2",
    "SANS_SENIOR_REGULAR": "AbbotsMortonSpaceportSansSenior-Regular.woff2",
    "SANS_SENIOR_BOLD": "AbbotsMortonSpaceportSansSenior-Bold.woff2",
    "MONO_REGULAR": "AbbotsMortonSpaceportMono-Regular.woff2",
}
FONT_DIR = Path("data") / "abbots-morton-spaceport"
MARKED_JS = Path("data") / "marked" / "marked.umd.js"

SHA256 = {
    FONT_DIR / FONTS["SANS_JUNIOR_REGULAR"]: (
        "f2a997c4725a84b347040dae4ff776170152fb8c23f5fd35e04bff98c1dc2028"
    ),
    FONT_DIR / FONTS["SANS_JUNIOR_BOLD"]: (
        "c788179a96b5fe0070f8c18d72c2021f87026b809940af7434e6a2636a9d7920"
    ),
    FONT_DIR / FONTS["SANS_SENIOR_REGULAR"]: (
        "09364498461369468ffa69c62f827581d096d6b45666705c94687f03d7bb70f8"
    ),
    FONT_DIR / FONTS["SANS_SENIOR_BOLD"]: (
        "088af65711523d3220e3449659f7404c4110bdefde7dd980bd6fa48d66eae316"
    ),
    FONT_DIR / FONTS["MONO_REGULAR"]: (
        "b4e9223937997b78ece9dcecbb3cfd8b4e0d1a9eaecde9316d74f8ae621e1a59"
    ),
    MARKED_JS: "7a1f8c5e7226b75ff16644bdb2c0130d2ae7371e7ea3106c2d6dac77ab0ff7b6",
}

SAMPLE_WORDS = (("hello", "ITJ"), ("world", "NN1"), ("quick", "AJ0"), ("script", "NN1"))
SAMPLE_HEADING = "# Quikscript Desk"
SAMPLE_PROSE = (
    "Write Markdown on the left and read it on the right. A Quikscript word the "
    "lexicon does not carry gets a dotted red underline; click an underlined word "
    "for the spellings it is nearest to."
)

CLOSING_SCRIPT = "</script"
PLACEHOLDER = re.compile(r"__QS_[A-Z_]+__")


class PageError(RuntimeError):
    pass


@dataclass(frozen=True)
class Record:
    latin: str
    pos: str
    qs: str
    junior: str
    x_letter: str
    frequency: int

    def columns(self) -> tuple[str, str, str]:
        return (self.qs, self.junior, self.x_letter)


@dataclass(frozen=True)
class Lexicon:
    """Everything the page checks a word against, derived from the master alone.

    `listed` is what the hunspell dictionary carries — the three columns and nothing else — and `union` is that plus the §III Senior contractions, which reach no column but are correct writing all the same. Everything held against the shipped `.dic` and `.aff` is held against `listed`; the one set the page checks against is `union`. The Junior/Senior toggle swaps the face alone, so neither grade needs a word set of its own.
    """

    listed: tuple[str, ...]
    union: tuple[str, ...]
    frequency: Mapping[str, int]


@dataclass(frozen=True)
class Coverage:
    """What the page carries, for the log.

    Every number is pinned in tests/test_desk.py, so this is a convenience for whoever is watching a change land rather than a check of its own.
    """

    lexicon: Lexicon
    size: int

    def report(self) -> str:
        return (
            f"{len(self.lexicon.union)} spellings — {len(self.lexicon.listed)} the "
            f"dictionary lists, plus "
            f"{len(self.lexicon.union) - len(self.lexicon.listed)} senior "
            f"contractions it does not\n"
            f"{self.size} bytes, self-contained"
        )


def artifact(name: str, root: Path) -> str:
    path = root / ARTIFACTS / name
    if not path.is_file():
        raise PageError(f"{path} not found; run `make artifacts` first")
    return path.read_text(encoding="utf-8")


def asset(name: Path, root: Path) -> bytes:
    """A vendored file's bytes, verified against the digest pinned above before use.

    The page inlines every one of these, so a font or a parser that had drifted would be baked into a generated file and shipped without a diff anyone could read. Provenance for both directories is in their own READMEs.
    """
    path = root / name
    if not path.is_file():
        raise PageError(
            f"vendored asset not found at {path}. It is checked in at {name} in a "
            f"source checkout; pass an explicit root when running from elsewhere."
        )
    data = path.read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != SHA256[name]:
        raise PageError(
            f"{path} has SHA-256 {actual}, expected {SHA256[name]}. The digest is "
            f"pinned in src/qslex/desk.py and in that directory's README; "
            f"bump both together."
        )
    return data


def load_records(root: Path) -> tuple[Record, ...]:
    """Every entry of the master, flattened in file order.

    The committed JSON is read rather than the corpus respelt: the page is projected from the artifact it ships beside, so a stale lexicon shows up as a stale page rather than as a page that quietly checks against a different word set than the hunspell dictionary next to it.
    """
    master = json.loads(artifact(LEXICON_JSON, root))
    return tuple(
        Record(
            latin=entry["Latn"],
            pos=entry["pos"],
            qs=entry["qs"],
            junior=entry.get("qs_junior", ""),
            x_letter=entry.get("qs_x", ""),
            frequency=entry["freq"],
        )
        for group in master["entries"].values()
        for entry in group
    )


def contracted(
    contractions: Iterable[Contraction], records: Iterable[Record]
) -> tuple[tuple[str, Record], ...]:
    """Each §III Senior contraction written out, beside every row it stands for.

    Only the `word` rows are taken. The two `clitic` rows stay out because neither can ever be a token the page checks: `n't` attaches solid, so it is never written on its own, and a bare `'ll` after an apostrophe is flagged here for the same reason the dictionary flags it, the apostrophe being deliberately outside `WORDCHARS` (docs/pipeline.md). A row's part-of-speech tag narrows the match to the rows carrying that tag; where it carries none, every row for the headword counts, and the rows are what the frequency the contraction inherits comes from.
    """
    rows: dict[str, list[Record]] = {}
    for record in records:
        rows.setdefault(record.latin.lower(), []).append(record)
    out: list[tuple[str, Record]] = []
    for entry in contractions:
        if entry.kind != WORD_ROW:
            continue
        matched = [
            record
            for record in rows.get(entry.word, ())
            if not entry.pos or record.pos == entry.pos
        ]
        if not matched:
            raise PageError(
                f"the contraction for {entry.word!r} ({entry.pos or 'any pos'}) "
                f"matches no row of {LEXICON_JSON}, so the page would carry a "
                f"spelling with no word to take a frequency from"
            )
        written = render_qs(parse(entry.contraction))
        out.extend((written, record) for record in matched)
    return tuple(out)


def derive(records: Iterable[Record], contractions: Iterable[Contraction]) -> Lexicon:
    """The one word set and the frequencies the page needs.

    A spelling's frequency is the highest any row writing it carries, in any column: an X-letter or junior form is the same word as the row's own spelling, so it inherits that row's count rather than falling to zero and sorting last in a suggestion list.

    The §III contractions join the union outright, which is what a Tier 2 facility is (docs/word-signs.md): correct writing the checker accepts whichever face is showing, never the spelling a column carries. Each takes the frequency of the word it contracts, so the suggester ranks it as common as that word.
    """
    rows = tuple(records)
    matched = contracted(contractions, rows)
    carried = frozenset(spellings((written, "", "") for written, _ in matched))

    frequency: dict[str, int] = {}
    for row in rows:
        for word in spellings((row.columns(),)):
            frequency[word] = max(frequency.get(word, 0), row.frequency)
    for written, row in matched:
        if written in carried:
            frequency[written] = max(frequency.get(written, 0), row.frequency)

    listed = spellings(row.columns() for row in rows)
    return Lexicon(
        listed=listed,
        union=tuple(sorted(frozenset(listed) | carried)),
        frequency=frequency,
    )


def crosscheck(lexicon: Lexicon, root: Path) -> None:
    """The page's word set and its TRY order, held to the shipped hunspell files.

    Both are re-derived here from the master rather than read out of the `.dic` and the `.aff`, so that the page and the dictionary cannot disagree quietly. They are the same two derivations `qslex.hunspell` makes for hunspell, so a mismatch means one of the two artifacts is stale, not that the page wants a wider set.

    What is held to the `.dic` is `listed`, the three columns alone. The page accepts the §III contractions on top of that, and its letter order stays the `.aff`'s TRY over the dictionary's own word set rather than one recounted over the wider one: the suggester is walking hunspell's alphabet, and 68 more spellings would not move it far enough to be worth two orders that have to be kept apart.
    """
    lines = artifact(HUNSPELL_DIC, root).splitlines()
    count, words = lines[0], tuple(lines[1:])
    if count != str(len(words)):
        raise PageError(f"{HUNSPELL_DIC} counts {count} entries and lists {len(words)}")
    if words != lexicon.listed:
        raise PageError(
            f"the page's {len(lexicon.listed)} listed spellings are not the "
            f"{len(words)} {HUNSPELL_DIC} lists; run `make artifacts`"
        )

    written = [
        line.removeprefix("TRY ")
        for line in artifact(HUNSPELL_AFF, root).splitlines()
        if line.startswith("TRY ")
    ]
    if len(written) != 1:
        raise PageError(f"{HUNSPELL_AFF} declares {len(written)} TRY lines, wanted 1")
    if written[0] != by_frequency(lexicon.listed):
        raise PageError(f"the page's letter order is not {HUNSPELL_AFF}'s TRY order")


def word_list(lexicon: Lexicon) -> str:
    """The word set and its frequencies as one string, one spelling to a line.

    A JSON object of 75,649 short keys is several hundred kilobytes of quoting and punctuation in a file that is fetched whole; a tab-separated block costs one split at startup and nothing else. The frequency is left off where it is zero, which is most of the list.
    """
    return "\n".join(
        f"{word}\t{lexicon.frequency[word]}" if lexicon.frequency[word] else word
        for word in lexicon.union
    )


def replacements() -> tuple[tuple[str, str], ...]:
    """Each X-letter bridged to the letter pair it stands for, both ways.

    The table the `.aff` writes as REP, and for the same reason: the letters around an X-letter change with it, so neither form of a word is a single-letter edit from the other and no edit-distance suggester alone will turn it up.
    """
    return tuple(
        (written, meant)
        for x_letter, pair in X_LETTERS
        for written, meant in ((x_letter, pair), (pair, x_letter))
    )


def confusions() -> tuple[str, ...]:
    """The letter groups a writer mistakes within, one group to a string.

    A phonemic script invites a particular misspelling: the right consonant skeleton around the wrong vowel, because the writer heard a vowel the accent or the schwa reduced to something else. So the suggester offers a candidate that stays inside a group ahead of every other single edit, however rare the word — a frequency rank alone buries a common word's contraction under consonant swaps that happen to be commoner. The vowels are the one group so far; a set of frequently confused consonants would be one more string here, sorted the same way.
    """
    return ("".join(sorted(chr(CODEPOINT_OF[name]) for name in VOWELS)),)


def variants(word: str) -> tuple[str, ...]:
    """The candidate misspellings of a word, in the order the sample tries them."""
    if len(word) < 2:
        return ()
    return (word[:-1], word[1:], word[1] + word[0] + word[2:])


def sample(records: Iterable[Record], lexicon: Lexicon) -> str:
    """The document the page opens with, built from the lexicon rather than typed.

    Every Quikscript spelling in it is looked up by (Latn, pos), so the sample cannot quietly stop being spelt the way the lexicon spells it. The one misspelling is the first candidate variant of the first sample word that the word set rejects, so the page opens with exactly one underline and something to click.
    """
    spelt = {(row.latin.lower(), row.pos): row.qs for row in records}
    missing = [key for key in SAMPLE_WORDS if not spelt.get(key)]
    if missing:
        raise PageError(f"the sample words are not all in the lexicon: {missing}")
    written = [spelt[key] for key in SAMPLE_WORDS]
    accepted = frozenset(lexicon.union)
    wrong = next((word for word in variants(written[0]) if word not in accepted), None)
    if wrong is None:
        raise PageError(f"every candidate variant of {SAMPLE_WORDS[0]} is a spelling")
    line = " ".join([*written, wrong])
    return "\n".join((SAMPLE_HEADING, "", SAMPLE_PROSE, "", line, ""))


def payload(lexicon: Lexicon) -> str:
    """Everything the page's JavaScript reads, as one JSON object.

    Sorted keys and a list of pairs for the replacement table, so that a rebuilt page differs only where the lexicon did.
    """
    data = {
        "confusions": list(confusions()),
        "rep": [list(pair) for pair in replacements()],
        "try_order": by_frequency(lexicon.listed),
        "words": word_list(lexicon),
    }
    return json.dumps(data, ensure_ascii=False, sort_keys=True)


def data_uri(raw: bytes) -> str:
    return "data:font/woff2;base64," + base64.b64encode(raw).decode("ascii")


def substitute(text: str, chunks: Mapping[str, str]) -> str:
    """Every placeholder filled, and nothing that could close the script it sits in.

    A chunk carrying `</script` would end its own element wherever the browser's tokenizer found the string, so the page would truncate quietly rather than fail to build. None of the inputs contains one; this is what keeps it that way.
    """
    for token, chunk in chunks.items():
        if CLOSING_SCRIPT in chunk.lower():
            raise PageError(f"{token} carries a {CLOSING_SCRIPT}, which would truncate")
        if token not in text:
            raise PageError(f"{token} is not in the template")
        text = text.replace(token, chunk)
    leftover = sorted(set(PLACEHOLDER.findall(text)))
    if leftover:
        raise PageError(f"the template has placeholders nothing filled: {leftover}")
    return text


def build(root: Path | None = None) -> tuple[str, Coverage]:
    root = root if root is not None else repo_root()
    records = load_records(root)
    lexicon = derive(records, load_contractions())
    crosscheck(lexicon, root)

    stylesheet = substitute(
        (WEB / STYLESHEET).read_text(encoding="utf-8"),
        {
            f"__QS_FONT_{key}__": data_uri(asset(FONT_DIR / name, root))
            for key, name in FONTS.items()
        },
    )
    page = substitute(
        (WEB / TEMPLATE).read_text(encoding="utf-8"),
        {
            "__QS_CSS__": stylesheet,
            "__QS_SAMPLE__": html.escape(sample(records, lexicon)),
            "__QS_MARKED__": asset(MARKED_JS, root).decode("utf-8"),
            "__QS_DATA__": payload(lexicon),
            "__QS_CORE__": (WEB / CORE).read_text(encoding="utf-8"),
            "__QS_APP__": (WEB / APP).read_text(encoding="utf-8"),
        },
    )
    return page, Coverage(lexicon, len(page.encode("utf-8")))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the Quikscript Desk page from the lexicon"
    )
    parser.add_argument("--out", type=Path, default=repo_root() / SITE / PAGE)
    parser.add_argument(
        "--check",
        action="store_true",
        help="rebuild in memory and fail if what is on disk differs",
    )
    args = parser.parse_args(argv)

    page, coverage = build()
    if not args.check:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(page, encoding="utf-8", newline="\n")
        print(f"wrote {args.out}")
        print()
        print(coverage.report())
        return 0

    stale = ""
    if not args.out.is_file():
        stale = f"{args.out} is missing"
    elif args.out.read_text(encoding="utf-8") != page:
        stale = f"{args.out} differs from a fresh build"
    if stale:
        print(stale)
        print("\nFAILED: 1 artifact(s) out of date; run `make site`")
        return 1
    print("OK: 1 artifact matches a fresh build")
    return 0


if __name__ == "__main__":
    sys.exit(main())
