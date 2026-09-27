"""The checker data shared by the Desk page and the editor server, derived from the lexicon JSON alone.

It computes the word set, frequencies, TRY order, REP table, confusion groups and lookup maps. The Desk page inlines this data, and the editor server reads it from the committed `editor/server/payload.json`. `crosscheck` compares the word set and TRY order with the committed hunspell files, so the page, the server and the dictionary accept the same spellings from the three columns.
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
COLUMNS = ("senior", "junior", "x")
CONTRACTION = "contraction"


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
    """The word sets and frequencies a checker uses, derived from the lexicon JSON alone.

    `listed` is the set the hunspell dictionary contains: the spellings in the three columns and nothing else. `union` adds the §III Senior contractions, which are in no column but are correct writing. Comparisons with the committed `.dic` and `.aff` use `listed`. A checker accepts `union`. The Junior/Senior toggle switches only the font, so neither grade needs its own word set.
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
    """Every entry of the lexicon JSON, flattened in file order.

    This reads the committed JSON rather than respelling the corpus, so the page and the payload are built from the same lexicon as the committed hunspell files. When the lexicon changes, the page and the payload no longer match a rebuild, and `make check` fails.
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
    """Each §III Senior contraction in PUA text, paired with every row it stands for.

    Only `word` rows are used. The two `clitic` rows are left out because a checker never receives either as a token. `n't` is written joined to its host word, so it never appears alone. The apostrophe is not in `WORDCHARS` (docs/pipeline.md), so in `'ll` the letters after the apostrophe are checked as a word of their own, and a checker flags them as hunspell does. A contraction row with a part-of-speech tag matches only rows with that tag. One with no tag matches every row for its word. The matched rows supply the frequency the contraction takes.
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
    """The word sets and the frequencies a checker needs.

    A spelling’s frequency is the highest frequency of any row with that spelling, in any column. An X-letter or junior form is the same word as the row’s senior spelling, so it gets that row’s frequency. A frequency of zero would sort it last in a suggestion list.

    The §III contractions are added to the union directly. docs/word-signs.md describes them as Tier 2: a checker accepts them as correct Senior writing, but no column contains them. Each takes the frequency of the word it contracts, so the suggester ranks it as common as that word.
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
    """Checks the word set and TRY order against the committed hunspell files.

    Both are derived from the lexicon JSON and then compared with the committed `.dic` and `.aff`, so a checker and the dictionary cannot disagree without this check failing. The derivations are the functions `qslex.hunspell` uses to write those files, so a mismatch means that either the lexicon JSON or the hunspell files are out of date.

    The `.dic` is compared with `listed`, the three columns alone. A checker also accepts the §III contractions, but its letter order is the `.aff`’s TRY order, computed over the dictionary’s word set rather than over `union`. The suggester uses hunspell’s letter order, and the few dozen extra spellings would barely change it, so there is one order instead of two.
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
    """The word set and its frequencies as one string, one spelling per line.

    A JSON object with one key per spelling would add several hundred kilobytes of quotes and punctuation to a file that is read whole. A tab-separated block needs only one split at startup. The frequency is omitted where it is zero.
    """
    return "\n".join(
        f"{word}\t{lexicon.frequency[word]}" if lexicon.frequency[word] else word
        for word in lexicon.union
    )


def replacements() -> tuple[tuple[str, str], ...]:
    """Each X-letter mapped to its two-letter pair, and the pair back to the X-letter.

    The `.aff` writes the same table as REP, for the same reason. Replacing an X-letter with its pair takes two single-letter edits, so the other form is not among the single-edit candidates, and an edit-distance search ranks it behind them.
    """
    return tuple(
        (written, meant)
        for x_letter, pair in X_LETTERS
        for written, meant in ((x_letter, pair), (pair, x_letter))
    )


def confusions() -> tuple[str, ...]:
    """The groups of letters a writer is likely to confuse, one group per string.

    In a phonemic script, a common misspelling has the right consonants around the wrong vowel. The writer hears a vowel that the lexicon’s accent, or reduction to schwa, spells differently. The suggester therefore lists substitutions within a group after the REP substitutions and before any other single-letter edit, however rare the resulting word. Ranking all single edits by frequency alone would put more frequent words reached by a consonant change ahead of the vowel fix. The vowels are the only group so far. A group of often-confused consonants would be one more string here, sorted the same way.
    """
    return ("".join(sorted(chr(CODEPOINT_OF[name]) for name in VOWELS)),)


def checker(lexicon: Lexicon) -> dict[str, object]:
    """Everything a checker reads, as one JSON-ready object.

    The Desk page inlines this object, and `editor/server/payload.json` contains it plus the two lookup maps. The keys are serialized in sorted order and the replacement table is a list of pairs, so a rebuilt file differs only where the lexicon changed.
    """
    return {
        "confusions": list(confusions()),
        "rep": [list(pair) for pair in replacements()],
        "try_order": by_frequency(lexicon.listed),
        "words": word_list(lexicon),
    }


def readings(records: Iterable[Record], contractions: Iterable[Contraction]) -> str:
    """The spelling-to-Latin map (`readings`), one entry per line, used for hover.

    Each line has a spelling, the row’s Latin word, its part-of-speech tag, and the column the spelling is in: `senior`, `junior`, `x`, or `contraction` for the §III forms that are in no column. The row’s other columns are not repeated here. A consumer looks the Latin word up in `writings` to find them. Spaced spellings are left out for the reason `spellings` drops them: no tokenizer ever passes one to a checker. As a result, the set of spellings in this map is exactly `union`.
    """
    rows = tuple(records)
    found: set[tuple[str, str, str, str]] = set()
    for row in rows:
        for column, value in zip(COLUMNS, row.columns(), strict=True):
            if value and " " not in value:
                found.add((value, row.latin, row.pos, column))
    for written, row in contracted(contractions, rows):
        if " " not in written:
            found.add((written, row.latin, row.pos, CONTRACTION))
    rank = {column: at for at, column in enumerate((*COLUMNS, CONTRACTION))}
    ordered = sorted(
        found, key=lambda entry: (entry[0], entry[1], entry[2], rank[entry[3]])
    )
    return "\n".join("\t".join(entry) for entry in ordered)


def writings(records: Iterable[Record]) -> str:
    """The Latin-to-spellings map (`writings`), one row per line, used for completions and the Latin lookup box.

    Each line has the lowercased Latin word, the part-of-speech tag, the frequency, and the three columns as the lexicon JSON has them, with junior and X-letter filled in only where they differ from senior. Heteronyms stay separate rows, so `read` keeps its two spellings apart by tag and `lead` keeps both of its nouns. Spaced spellings are blanked for the reason `spellings` drops them: a completion inserts one token, never a phrase the tokenizer would split apart again.
    """
    found: set[tuple[str, str, int, str, str, str]] = set()
    for row in records:
        qs, junior, x_letter = (
            value if " " not in value else "" for value in row.columns()
        )
        if qs or junior or x_letter:
            found.add((row.latin.lower(), row.pos, row.frequency, qs, junior, x_letter))
    return "\n".join(
        f"{latin}\t{pos}\t{frequency}\t{qs}\t{junior}\t{x_letter}"
        for latin, pos, frequency, qs, junior, x_letter in sorted(found)
    )


def payload(lexicon: Lexicon) -> str:
    """The checker object as the JSON text the Desk page inlines, with the same `json.dumps` options `qslex.payload` uses."""
    return json.dumps(checker(lexicon), ensure_ascii=False, sort_keys=True)
