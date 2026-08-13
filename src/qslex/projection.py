"""The derivation every Quikscript spelling checker shares, from the master alone.

The Desk page inlines it and the editor server reads it from a committed payload, but it is one projection: the union word set with its frequencies, the suggestion tables, and the crosschecks that hold them to the shipped hunspell artifacts. One derivation with several consumers is what keeps the page, the server and the dictionary from ever quietly disagreeing about what is a misspelling.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from qslex.build import ARTIFACTS, HUNSPELL_AFF, HUNSPELL_DIC, LEXICON_JSON
from qslex.csur import CODEPOINT_OF
from qslex.hunspell import X_LETTERS, by_frequency, spellings
from qslex.letters import VOWELS, parse, render_qs
from qslex.words import Contraction

WORD_ROW = "word"


class ProjectionError(RuntimeError):
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
    """Everything a checker holds a word against, derived from the master alone.

    `listed` is what the hunspell dictionary carries — the three columns and nothing else — and `union` is that plus the §III Senior contractions, which reach no column but are correct writing all the same. Everything held against the shipped `.dic` and `.aff` is held against `listed`; the one set a checker accepts is `union`. A Junior/Senior toggle swaps the face alone, so neither grade needs a word set of its own.
    """

    listed: tuple[str, ...]
    union: tuple[str, ...]
    frequency: Mapping[str, int]


def artifact(name: str, root: Path) -> str:
    path = root / ARTIFACTS / name
    if not path.is_file():
        raise ProjectionError(f"{path} not found; run `make artifacts` first")
    return path.read_text(encoding="utf-8")


def load_records(root: Path) -> tuple[Record, ...]:
    """Every entry of the master, flattened in file order.

    The committed JSON is read rather than the corpus respelled: every projection is built from the artifact it ships beside, so a stale lexicon shows up as a stale page or payload rather than as a checker that quietly checks against a different word set than the hunspell dictionary next to it.
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

    Only the `word` rows are taken. The two `clitic` rows stay out because neither can ever be a token a checker meets: `n't` attaches solid, so it is never written on its own, and a bare `'ll` after an apostrophe is flagged here for the same reason the dictionary flags it, the apostrophe being deliberately outside `WORDCHARS` (docs/pipeline.md). A row’s part-of-speech tag narrows the match to the rows carrying that tag; where it carries none, every row for the headword counts, and the rows are what the frequency the contraction inherits comes from.
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
            raise ProjectionError(
                f"the contraction for {entry.word!r} ({entry.pos or 'any pos'}) "
                f"matches no row of {LEXICON_JSON}, so the projection would carry a "
                f"spelling with no word to take a frequency from"
            )
        written = render_qs(parse(entry.contraction))
        out.extend((written, record) for record in matched)
    return tuple(out)


def derive(records: Iterable[Record], contractions: Iterable[Contraction]) -> Lexicon:
    """The one word set and the frequencies a checker needs.

    A spelling’s frequency is the highest any row writing it carries, in any column: an X-letter or junior form is the same word as the row’s own spelling, so it inherits that row’s count rather than falling to zero and sorting last in a suggestion list.

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
    """The projection’s word set and its TRY order, held to the shipped hunspell files.

    Both are re-derived here from the master rather than read out of the `.dic` and the `.aff`, so that a checker and the dictionary cannot disagree quietly. They are the same two derivations `qslex.hunspell` makes for hunspell, so a mismatch means one of the two artifacts is stale, not that the projection wants a wider set.

    What is held to the `.dic` is `listed`, the three columns alone. A checker accepts the §III contractions on top of that, and its letter order stays the `.aff`’s TRY over the dictionary’s own word set rather than one recounted over the wider one: the suggester is walking hunspell’s alphabet, and a few dozen more spellings would not move it far enough to be worth two orders that have to be kept apart.
    """
    lines = artifact(HUNSPELL_DIC, root).splitlines()
    count, words = lines[0], tuple(lines[1:])
    if count != str(len(words)):
        raise ProjectionError(
            f"{HUNSPELL_DIC} counts {count} entries and lists {len(words)}"
        )
    if words != lexicon.listed:
        raise ProjectionError(
            f"the projection’s {len(lexicon.listed)} listed spellings are not the "
            f"{len(words)} {HUNSPELL_DIC} lists; run `make artifacts`"
        )

    written = [
        line.removeprefix("TRY ")
        for line in artifact(HUNSPELL_AFF, root).splitlines()
        if line.startswith("TRY ")
    ]
    if len(written) != 1:
        raise ProjectionError(
            f"{HUNSPELL_AFF} declares {len(written)} TRY lines, wanted 1"
        )
    if written[0] != by_frequency(lexicon.listed):
        raise ProjectionError(
            f"the projection’s letter order is not {HUNSPELL_AFF}’s TRY order"
        )


def word_list(lexicon: Lexicon) -> str:
    """The word set and its frequencies as one string, one spelling to a line.

    A JSON object of tens of thousands of short keys is several hundred kilobytes of quoting and punctuation in a file that is read whole; a tab-separated block costs one split at startup and nothing else. The frequency is left off where it is zero, which is most of the list.
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

    A phonemic script invites a particular misspelling: the right consonant skeleton around the wrong vowel, because the writer heard a vowel the accent or the schwa reduced to something else. So the suggester offers a candidate that stays inside a group ahead of every other single edit, however rare the word — a frequency rank alone buries a common word’s contraction under consonant swaps that happen to be commoner. The vowels are the one group so far; a set of frequently confused consonants would be one more string here, sorted the same way.
    """
    return ("".join(sorted(chr(CODEPOINT_OF[name]) for name in VOWELS)),)


def payload(lexicon: Lexicon) -> str:
    """Everything a checker reads, as one JSON object.

    The Desk page inlines this string and `editor/server/payload.json` commits it, one build product with two consumers. Sorted keys and a list of pairs for the replacement table, so that a rebuilt projection differs only where the lexicon did.
    """
    data = {
        "confusions": list(confusions()),
        "rep": [list(pair) for pair in replacements()],
        "try_order": by_frequency(lexicon.listed),
        "words": word_list(lexicon),
    }
    return json.dumps(data, ensure_ascii=False, sort_keys=True)
