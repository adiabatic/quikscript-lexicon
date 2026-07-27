from __future__ import annotations

import dataclasses
import re
from collections.abc import Callable, Container, Iterable
from dataclasses import dataclass, field
from pathlib import Path

from qslex.elements import DIVIDERS, elements
from qslex.letters import Letter, Letters, names, parse, render, unknown_names
from qslex.tables import rows_of
from qslex.tokenizer import Token, is_stressed
from qslex.words import Signs, apply_signs, load_word_signs

RULE_WORDS_FILE = "rule-words.tsv"
RULE_WORDS_HEADER = ["rule", "word", "decision", "authority", "note"]
DECISIONS = {"apply", "skip"}
GATED_RULES = {
    "prefix-be-de-re",
    "terminal-ess-est",
    "terminal-ful",
    "terminal-ing",
    "terminal-y",
}

LIGATURES_FILE = "x-ligatures.tsv"
LIGATURES_HEADER = ["word", "ligature", "reason", "note"]
LIGATURE_REASONS = {"multiple-x", "unaligned"}
LIGATURE_LETTERS = frozenset({"Excite", "Exam"})

EPENTHESIS = "Ə"

# The Manual names the seven consonant pairs that force a separating vowel: "Between
# these — SZ, ShZ, ChZ, JZ, ZZ, DD, TD — some kind of vowel has to be uttered." ReadLex
# tags most of those sites with a capital Ə; where it wrote a plain ə instead, the pair
# itself identifies the site.
EPENTHETIC_PAIRS = frozenset(
    {
        ("See", "Zoo"),
        ("She", "Zoo"),
        ("Cheer", "Zoo"),
        ("Jay", "Zoo"),
        ("Zoo", "Zoo"),
        ("Day", "Day"),
        ("Tea", "Day"),
    }
)

REDUCIBLE = frozenset({"It", "Utter"})
UNREDUCED = frozenset({"Eat"})
Y_REDUCIBLE = REDUCIBLE | UNREDUCED
ING_TAILS = ("ingness", "ingly", "ings", "ing")


@dataclass(frozen=True)
class Context:
    latin: str
    pos: str
    ipa: str
    tokens: tuple[Token, ...]
    final: bool = True

    def within(self, latin: str, final: bool) -> Context:
        """The same row seen as one element of its own entry.

        A rule reads the Latin spelling, the part-of-speech tag, and whether the entry
        ends here; the IPA and its tokens ride along whole, because nothing after
        `naive` looks at them.
        """
        return dataclasses.replace(self, latin=latin, final=final)


@dataclass(frozen=True)
class Spelling:
    senior: str
    junior: str
    ligature: str
    applied: tuple[str, ...]
    ruled: tuple[tuple[str, str], ...]
    signed: tuple[str, ...]
    signs: tuple[tuple[str, str], ...]
    elements: tuple[Element, ...]


def naive(context: Context) -> Letters:
    out: list[Letter] = []
    position = 0
    for token in context.tokens:
        following = position + len(token.ipa)
        if token.entry.kind == "hiatus":
            position = following
            continue
        if token.entry.kind == "structural":
            out.append(Letter(token.ipa, False, token.ipa))
            position = following
            continue
        stressed = is_stressed(context.ipa, position)
        for offset, name in enumerate(token.entry.letters):
            out.append(Letter(name, stressed and offset == 0, token.ipa))
        position = following
    return tuple(out)


def _drop(letters: Letters, index: int) -> Letters:
    return letters[:index] + letters[index + 1 :]


def _insert(letters: Letters, index: int, name: str) -> Letters:
    return letters[:index] + (Letter(name, False, ""),) + letters[index:]


def _rename(letters: Letters, index: int, name: str) -> Letters:
    if letters[index].name == name:
        return letters
    return (
        letters[:index]
        + (dataclasses.replace(letters[index], name=name),)
        + letters[index + 1 :]
    )


def _offset(match: re.Match[str], letters: Letters) -> int:
    """Trailing letters spelling the inflection this rule's pattern looked through."""
    if match.groups()[-1] and letters and letters[-1].name in {"Zoo", "See"}:
        return 1
    return 0


def _ends(letters: Letters, offset: int, *wanted: str) -> bool:
    end = len(letters) - offset
    start = end - len(wanted)
    return start >= 0 and names(letters[start:end]) == wanted


def _vowel_at(letters: Letters, offset: int, span: int) -> int | None:
    """Index of the vowel `span` letters in from the end, past the inflection."""
    index = len(letters) - offset - span - 1
    if index < 1 or not letters[index].is_vowel:
        return None
    return index


def _reducible(letters: Letters, index: int, among: frozenset[str] = REDUCIBLE) -> bool:
    return not letters[index].stressed and letters[index].name in among


def _force(
    letters: Letters,
    offset: int,
    shape: tuple[str, ...],
    want: str,
    among: frozenset[str] = REDUCIBLE,
) -> Letters:
    """Normalise the vowel that precedes `shape` at the end of the word.

    `among` names the vowels this rule may rewrite, and only terminal -y widens it.
    Read reserves ·Eat "for distinction where the terminal is stressed", so an
    unstressed ·Eat at that terminal is a vowel he prescribes over; everywhere else a
    full ·Eat is a vowel ReadLex means, as **·Et is not a reducible vowel** in
    docs/orthographic-rules.md says of ·Et.
    """
    if not _ends(letters, offset, *shape):
        return letters
    index = _vowel_at(letters, offset, len(shape))
    if index is None or not _reducible(letters, index, among):
        return letters
    return _rename(letters, index, want)


def _restored(context: Context) -> bool:
    """Whether the vowel before a word-final L comes back, another syllable following.

    "Where another syllable is added, the vowel sound before this L must be clearly
    pronounced and spelt in most cases: as it must be in — finally, orally, animality,
    initially, officially, levelling, devilry, caviller, rif(u)leman." A following
    element of a compound adds a syllable exactly as a suffix does, so able-bodied and
    cable-car keep the vowel that able and cable drop.
    """
    return not context.final


def _omit(letters: Letters, offset: int, shape: tuple[str, ...]) -> Letters:
    """Drop the unstressed vowel that precedes `shape`, unless a vowel precedes it."""
    if not _ends(letters, offset, *shape):
        return letters
    index = _vowel_at(letters, offset, len(shape))
    if index is None or not _reducible(letters, index):
        return letters
    if letters[index - 1].is_vowel:
        return letters
    return _drop(letters, index)


@dataclass(frozen=True)
class RuleWord:
    rule: str
    word: str
    decision: str
    authority: str
    note: str


@dataclass(frozen=True)
class LigatureRule:
    word: str
    ligature: str
    reason: str
    note: str


@dataclass(frozen=True)
class Tables:
    words: dict[tuple[str, str], RuleWord] = field(default_factory=dict)
    ligatures: dict[str, LigatureRule] = field(default_factory=dict)
    signs: Signs = field(default_factory=dict)

    def skipped(self, rule: str, latin: str) -> bool:
        entry = self.words.get((rule, latin))
        return entry is not None and entry.decision == "skip"

    def ruled(self, rule: str, latin: str) -> bool:
        return (rule, latin) in self.words

    def consulted(
        self, fired: Iterable[str], latin: str
    ) -> tuple[tuple[str, str], ...]:
        """The rulings this word reached: one it fired under, or one that stopped it."""
        keys = {(rule, latin) for rule in fired}
        keys.update((rule, latin) for rule in GATED_RULES if self.skipped(rule, latin))
        return tuple(sorted(keys & self.words.keys()))

    def ligature_for(self, latin: str) -> LigatureRule | None:
        return self.ligatures.get(latin)


NO_TABLES = Tables()


def load_rule_words(path: Path | None = None) -> dict[tuple[str, str], RuleWord]:
    known: dict[tuple[str, str], RuleWord] = {}
    for lineno, source, row in rows_of(path, RULE_WORDS_FILE, RULE_WORDS_HEADER):
        entry = RuleWord(*row)
        if entry.rule not in GATED_RULES:
            raise ValueError(
                f"{source}:{lineno}: {entry.rule!r} is not a gated rule "
                f"(have {sorted(GATED_RULES)})"
            )
        if entry.decision not in DECISIONS:
            raise ValueError(
                f"{source}:{lineno}: decision must be one of {sorted(DECISIONS)}, "
                f"got {entry.decision!r}"
            )
        if entry.rule == "terminal-ing" and not entry.word.endswith(ING_TAILS):
            raise ValueError(f"{source}:{lineno}: {entry.word!r} has no -ing")
        if not entry.authority:
            raise ValueError(f"{source}:{lineno}: a decision needs an authority")
        key = (entry.rule, entry.word)
        if key in known:
            raise ValueError(f"{source}:{lineno}: duplicate row for {key}")
        known[key] = entry
    return known


def load_x_ligatures(path: Path | None = None) -> dict[str, LigatureRule]:
    known: dict[str, LigatureRule] = {}
    for lineno, source, row in rows_of(path, LIGATURES_FILE, LIGATURES_HEADER):
        rule = LigatureRule(*row)
        if rule.reason not in LIGATURE_REASONS:
            raise ValueError(
                f"{source}:{lineno}: reason must be one of "
                f"{sorted(LIGATURE_REASONS)}, got {rule.reason!r}"
            )
        if "x" not in rule.word:
            raise ValueError(f"{source}:{lineno}: {rule.word!r} has no x to ligate")
        if not rule.note:
            raise ValueError(f"{source}:{lineno}: every ligature call needs a note")
        unknown = unknown_names(rule.ligature)
        if unknown:
            raise ValueError(f"{source}:{lineno}: unknown letter names {unknown}")
        spelt = names(parse(rule.ligature))
        if rule.ligature and not LIGATURE_LETTERS.intersection(spelt):
            raise ValueError(
                f"{source}:{lineno}: {rule.ligature} carries no ligature; leave "
                f"the column empty to rule that this word takes none"
            )
        if "xc" in rule.word and any(
            first in LIGATURE_LETTERS and second == "See"
            for first, second in zip(spelt, spelt[1:], strict=False)
        ):
            raise ValueError(
                f"{source}:{lineno}: {rule.ligature} adds a ·See after the "
                f"ligature that the ligature already covers"
            )
        if rule.word in known:
            raise ValueError(f"{source}:{lineno}: duplicate row for {rule.word!r}")
        known[rule.word] = rule
    return known


def load_tables() -> Tables:
    return Tables(load_rule_words(), load_x_ligatures(), load_word_signs())


def apply_es_ed(context: Context, letters: Letters) -> Letters:
    kept = tuple(f for f in letters if f.source != EPENTHESIS)
    if ES_ED.search(context.latin) is None:
        return kept
    for index in range(1, len(kept) - 1):
        pair = (kept[index - 1].name, kept[index + 1].name)
        if (
            kept[index].name == "Utter"
            and kept[index].source == "ə"
            and not kept[index].stressed
            and pair in EPENTHETIC_PAIRS
        ):
            return _drop(kept, index)
    return kept


def apply_con_com(context: Context, letters: Letters) -> Letters:
    latin = context.latin
    if len(latin) < 5 or not latin.startswith(("con", "com")):
        return letters
    consonant = "May" if latin[2] == "m" else "No"
    if not _ends(letters[:3], 0, "Key", "Utter", consonant):
        return letters
    if letters[1].stressed:
        return letters
    return _drop(letters, 1)


@dataclass(frozen=True)
class PrefixForm:
    """One prefix whose vowel the Manual normalises.

    `spellings` are the Latin openings that select the form, `index` the letter it
    rewrites and `want` what that letter becomes; `frame` names the consonants that
    have to sit where they do for the prefix to be the real one.
    """

    spellings: tuple[str, ...]
    index: int
    want: str
    frame: tuple[tuple[int, str], ...]


def _prefix(context: Context, letters: Letters, form: PrefixForm) -> Letters:
    """Normalise the prefix vowel, once the form's frame confirms the consonants."""
    if len(letters) <= max(form.index, *(at for at, _ in form.frame)):
        return letters
    if any(letters[at].name != name for at, name in form.frame):
        return letters
    if not _reducible(letters, form.index):
        return letters
    return _rename(letters, form.index, form.want)


PREFIX_FORMS: dict[str, tuple[PrefixForm, ...]] = {
    "prefix-un": (PrefixForm(("un",), 0, "Utter", ((1, "No"),)),),
    "prefix-an-al-ar": (
        PrefixForm(("an",), 0, "Utter", ((1, "No"),)),
        PrefixForm(("al",), 0, "Utter", ((1, "Low"),)),
        PrefixForm(("ar",), 0, "Utter", ((1, "Roe"),)),
    ),
    "prefix-ob-of": (
        PrefixForm(("ob",), 0, "Utter", ((1, "Bay"),)),
        PrefixForm(("of",), 0, "Utter", ((1, "Fee"),)),
    ),
    "prefix-be-de-re": (
        PrefixForm(("be",), 1, "It", ((0, "Bay"),)),
        PrefixForm(("de",), 1, "It", ((0, "Day"),)),
        PrefixForm(("re",), 1, "It", ((0, "Roe"),)),
    ),
    "prefix-pre-pro": (
        PrefixForm(("pre",), 2, "It", ((0, "Pea"), (1, "Roe"))),
        PrefixForm(("pro",), 2, "Utter", ((0, "Pea"), (1, "Roe"))),
    ),
    "prefix-per-pur": (
        PrefixForm(("per", "pur"), 1, "Utter", ((0, "Pea"), (2, "Roe"))),
    ),
    "prefix-in-en": (PrefixForm(("in", "en"), 0, "It", ((1, "No"),)),),
}


def _prefixed(context: Context, letters: Letters, rule: str) -> Letters:
    for form in PREFIX_FORMS[rule]:
        if context.latin.startswith(form.spellings):
            return _prefix(context, letters, form)
    return letters


def _ing_stem(latin: str) -> str:
    return latin[: latin.rindex("ing")]


def apply_ing(context: Context, letters: Letters) -> Letters:
    latin = context.latin
    if not latin.endswith(ING_TAILS):
        return letters
    if _ing_stem(latin).endswith("y"):
        return letters
    for index in range(len(letters) - 2, 0, -1):
        if letters[index].name == "It" and letters[index + 1].name == "Oolong":
            return _drop(letters, index)
    return letters


def apply_ally(context: Context, letters: Letters, match: re.Match[str]) -> Letters:
    offset = _offset(match, letters)
    if match.group(1) == "ally":
        if not _ends(letters, offset, "Low", "It"):
            return letters
        index = len(letters) - offset - 2
        if letters[index - 1].is_vowel:
            return _force(letters, offset, ("Low", "It"), "Utter")
        return _insert(letters, index, "Utter")
    if match.group(1) in {"ably", "ibly"}:
        return _omit(letters, offset, ("Low", "It"))
    if _restored(context):
        return letters
    return _omit(letters, offset, ("Low",))


def apply_tion(context: Context, letters: Letters, match: re.Match[str]) -> Letters:
    return _omit(letters, _offset(match, letters), ("No",))


def apply_ess(context: Context, letters: Letters, match: re.Match[str]) -> Letters:
    shape = ("See", "Tea") if match.group(1) == "est" else ("See",)
    return _force(letters, _offset(match, letters), shape, "Et")


def apply_land(context: Context, letters: Letters, match: re.Match[str]) -> Letters:
    if match.group(1) == "men":
        return letters
    offset = _offset(match, letters)
    for shape in (("No", "Day"), ("No", "Tea"), ("No",)):
        after = _omit(letters, offset, shape)
        if after != letters:
            return after
    return letters


def apply_ent(context: Context, letters: Letters, match: re.Match[str]) -> Letters:
    offset = _offset(match, letters)
    for shape in (("No", "Tea"), ("No", "See")):
        after = _force(letters, offset, shape, "Utter")
        if after != letters:
            return after
    return letters


def apply_ous(context: Context, letters: Letters, match: re.Match[str]) -> Letters:
    return _force(letters, _offset(match, letters), ("See",), "Utter")


def apply_er(context: Context, letters: Letters, match: re.Match[str]) -> Letters:
    return _force(letters, _offset(match, letters), ("Roe",), "Utter")


def apply_ier(context: Context, letters: Letters, match: re.Match[str]) -> Letters:
    return _tighten(letters, _offset(match, letters), ("Utter", "Roe"))


def apply_ia(context: Context, letters: Letters, match: re.Match[str]) -> Letters:
    offset = _offset(match, letters)
    for shape in (("Utter", "No"), ("Utter",)):
        after = _tighten(letters, offset, shape)
        if after != letters:
            return after
    return letters


def _tighten(letters: Letters, offset: int, shape: tuple[str, ...]) -> Letters:
    """The -ia/-ier vowel: ·It when unstressed, ·Eat when stressed."""
    if not _ends(letters, offset, *shape):
        return letters
    index = _vowel_at(letters, offset, len(shape))
    if index is None or letters[index].name not in {"It", "Eat"}:
        return letters
    return _rename(letters, index, "Eat" if letters[index].stressed else "It")


def apply_y(context: Context, letters: Letters, match: re.Match[str]) -> Letters:
    """Write the unstressed terminal ·It, seeing through a plural -s.

    An -es after a silent e spells a plural of its own — houses, similes — and the
    vowel that plural adds is its own, always a reduced one. Only a full ·Eat there
    can be the terminal, which leaves apogees carrying apogee's and theses carrying
    the Greek ending's, a difference no Latin string holds: see `_y_plural`.
    """
    among = UNREDUCED if _y_plural(match) else Y_REDUCIBLE
    return _force(letters, _offset(match, letters), (), "It", among)


def _y_plural(match: re.Match[str]) -> bool:
    """Whether the -s this terminal saw through follows an -e rather than an -ie or -y.

    latchkeys and rabies say in the Latin that the terminal is theirs and the -s is an
    inflection on it. An -es does not: it is equally how English spells the plural of a
    silent -e and how Greek and Latin spell an ending of their own, so theses is not
    these plus s and vortices is not vortice plus s, while apogees is apogee plus s.
    """
    return bool(match.group(2)) and match.group(1) == "e"


def apply_ain(context: Context, letters: Letters, match: re.Match[str]) -> Letters:
    return _force(letters, _offset(match, letters), ("No",), "Utter")


def apply_age(context: Context, letters: Letters, match: re.Match[str]) -> Letters:
    latin = context.latin
    stem = latin[: latin.rindex("age")]
    want = "It" if stem.endswith(("y", "i")) else "Utter"
    return _force(letters, _offset(match, letters), ("Jay",), want)


def apply_ward(context: Context, letters: Letters, match: re.Match[str]) -> Letters:
    offset = _offset(match, letters)
    if not _ends(letters, offset, "Way", "Utter", "Roe", "Day"):
        return letters
    index = len(letters) - offset - 3
    if letters[index].stressed:
        return letters
    return _drop(_drop(letters, index), index)


def apply_ful(context: Context, letters: Letters, match: re.Match[str]) -> Letters:
    offset = _offset(match, letters)
    shape = ("Low", "It") if match.group(1) else ("Low",)
    if not _ends(letters, offset, *shape):
        return letters
    index = _vowel_at(letters, offset, len(shape))
    if index is None or letters[index - 1].name != "Fee":
        return letters
    if letters[index].stressed or letters[index].name not in {"Utter", "Foot"}:
        return letters
    return _rename(letters, index, "Foot" if context.pos.startswith("NN") else "Utter")


def apply_al(context: Context, letters: Letters, match: re.Match[str]) -> Letters:
    if _restored(context):
        return letters
    return _omit(letters, _offset(match, letters), ("Low",))


def apply_en_on(context: Context, letters: Letters, match: re.Match[str]) -> Letters:
    return _force(letters, _offset(match, letters), ("No",), "Utter")


Apply = Callable[[Context, Letters], Letters]
ApplyTerminal = Callable[[Context, Letters, re.Match[str]], Letters]


@dataclass(frozen=True)
class Rule:
    id: str
    apply: Apply


@dataclass(frozen=True)
class Terminal:
    """A rule keyed to the end of a word, run on the match that selected it."""

    id: str
    apply: ApplyTerminal
    latin: re.Pattern[str]


def _pattern(body: str) -> re.Pattern[str]:
    return re.compile(rf"(?<=.){body}")


ES_ED = _pattern(r"(es|ed)(s|ness|ly)?$")
ALLY = _pattern(r"(ally|ably|ibly|able|ible)(s)?$")
TION = _pattern(r"(shion|tion|cean|sion|gion)(s|es)?$")
ESS = _pattern(r"(est|ess)(es)?$")
LAND = _pattern(r"(land|ment|man|men)(s)?$")
ENT = _pattern(r"(ence|ance|ent|ant)(s)?$")
OUS = _pattern(r"(us)(es)?$")
WARD = _pattern(r"ward(s)?$")
FUL = _pattern(r"ful(ly)?(s)?$")
AIN = _pattern(r"ain(s)?$")
AGE = _pattern(r"age(s)?$")
AL = _pattern(r"(al|el|le|il)(s)?$")
IA = _pattern(r"(ian|ean|ion|ia|ea)(s)?$")
IER = _pattern(r"(ier|ior)(s)?$")
ER = _pattern(r"(er|ar|ir|or|our|yr|re)(s)?$")
YY = _pattern(r"(ie|y|e)(s)?$")
EN = _pattern(r"(en|on)(s)?$")


def _prefix_rule(rule: str) -> Rule:
    def apply(context: Context, letters: Letters) -> Letters:
        return _prefixed(context, letters, rule)

    return Rule(rule, apply)


PREFIX_RULES: tuple[Rule, ...] = (Rule("prefix-con-com", apply_con_com),) + tuple(
    _prefix_rule(rule) for rule in PREFIX_FORMS
)

TERMINAL_RULES: tuple[Terminal, ...] = (
    Terminal("terminal-ally-able", apply_ally, ALLY),
    Terminal("terminal-tion", apply_tion, TION),
    Terminal("terminal-ess-est", apply_ess, ESS),
    Terminal("terminal-land-ment", apply_land, LAND),
    Terminal("terminal-ent-ance", apply_ent, ENT),
    Terminal("terminal-us-ous", apply_ous, OUS),
    Terminal("terminal-ward", apply_ward, WARD),
    Terminal("terminal-ful", apply_ful, FUL),
    Terminal("terminal-ain", apply_ain, AIN),
    Terminal("terminal-age", apply_age, AGE),
    Terminal("terminal-al-el-le-il", apply_al, AL),
    Terminal("terminal-ia-ea", apply_ia, IA),
    Terminal("terminal-ier-ior", apply_ier, IER),
    Terminal("terminal-er", apply_er, ER),
    Terminal("terminal-y", apply_y, YY),
    Terminal("terminal-en-on", apply_en_on, EN),
)

WORD_RULES: tuple[Rule, ...] = (
    Rule("terminal-es-ed", apply_es_ed),
    Rule("terminal-ing", apply_ing),
) + PREFIX_RULES

RULES: tuple[Rule | Terminal, ...] = WORD_RULES + TERMINAL_RULES

RULE_IDS = tuple(rule.id for rule in RULES)


def claims(terminal: Terminal, context: Context) -> bool:
    """Whether this terminal owns the end of the word, fire or not."""
    return terminal.latin.search(context.latin) is not None


def terminal_for(context: Context) -> tuple[Terminal, re.Match[str]] | None:
    """The terminal that owns the end of this word, and the match that selected it."""
    for rule in TERMINAL_RULES:
        match = rule.latin.search(context.latin)
        if match is not None:
            return rule, match
    return None


@dataclass(frozen=True)
class Element:
    """One part of an entry, with the run of the spelling that belongs to it.

    A `word` is what the rules run on: not the separators, and not the empty word an
    entry that begins or ends with one leaves behind.
    """

    context: Context
    letters: Letters

    @property
    def word(self) -> bool:
        return bool(self.context.latin) and self.context.latin not in DIVIDERS


def split(context: Context, letters: Letters) -> tuple[Element, ...]:
    """The entry cut into the words the terminals and prefixes actually attach to.

    A terminal is keyed to the end of a word and a prefix to the start of one, so a
    hyphenated or multi-word entry has to be cut up before either can see the words
    inside it: matching the whole entry string leaves a terminal for the last element
    only and a prefix for the first, and every element between them keeps a vowel the
    Manual drops. The cut is `qslex.elements`', alignment guard and all, so that the
    rules and the word signs cannot disagree about where a boundary is; an entry the
    guard rejects comes back whole, as a single element.

    Only the element the entry ends on is final, which is why a prefix-form entry like
    after- has none: something follows its last word, even if the corpus does not say
    what.
    """
    pairs = elements(context.latin, letters)
    if pairs is None:
        return (Element(context, letters),)
    last = len(pairs) - 1
    return tuple(
        Element(context.within(part, index == last), run)
        for index, (part, run) in enumerate(pairs)
    )


def _pairs(letters: Letters) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for index in range(len(letters) - 1):
        pair = (letters[index].name, letters[index + 1].name)
        if pair == ("Key", "See"):
            found.append((index, "Excite"))
        elif pair == ("Gay", "Zoo"):
            found.append((index, "Exam"))
    return found


def ligatable(spelling: str) -> bool:
    """Whether a shipped spelling still carries a pair the ligature would cover."""
    return bool(_pairs(parse(spelling)))


def ligate(context: Context, letters: Letters, tables: Tables) -> Letters | None:
    latin = context.latin
    declared = tables.ligature_for(latin)
    if declared is not None:
        return parse(declared.ligature) if declared.ligature else None
    if latin.count("x") != 1:
        return None
    pairs = _pairs(letters)
    if len(pairs) != 1:
        return None
    index, name = pairs[0]
    out = _rename(_drop(letters, index + 1), index, name)
    initial = latin.startswith("ex") and index == 1 and out[0].name == "It"
    if initial and not out[0].stressed:
        out = _rename(out, 0, "Et")
    return out


def undecided_ing(latin: str, participles: Container[str]) -> bool:
    """An -ing word no participle decides, so root-or-affix is a ruling, not a guess.

    A word that is, or ends in, something ReadLex tags VVG is an affix by construction
    — no root -ing word is ever a present participle. Everything else (roots, the
    -ling noun suffix, placenames, lexicalised participles) is ruled on by hand in
    rule-words.tsv.
    """
    if not latin.endswith(ING_TAILS):
        return False
    base = latin
    for tail in ("ness", "ly", "s"):
        if base.endswith(tail) and base[: -len(tail)].endswith("ing"):
            base = base[: -len(tail)]
            break
    if _ing_stem(base).endswith("y"):
        return False
    return not any(base[index:] in participles for index in range(len(base)))


def undecided_prefix(context: Context, letters: Letters, tables: Tables) -> bool:
    """A be-/de-/re- rewrite means ReadLex disagreed with the Manual, so rule on it.

    Nothing in the data separates the Manual's begin and decide, where the prefix is
    real, from Berlin and Denise, where the letters merely start the same way. The rule
    therefore fires on the Latin string and every word it would touch is ruled on.
    """
    if tables.ruled("prefix-be-de-re", context.latin):
        return False
    return _prefixed(context, letters, "prefix-be-de-re") != letters


def undecided_ess(context: Context, letters: Letters, tables: Tables) -> bool:
    """A -est/-ess rewrite starting from ·It rather than schwa wants a ruling.

    The Manual standardises the *variable* unstressed vowel of this terminal, which
    ReadLex writes as schwa. An ·It there is evidence that the Latin -est/-ess is the
    root rather than the suffix (forest, harvest, tempest, Furness), so every one is
    ruled on in rule-words.tsv rather than rewritten on the strength of the spelling.
    """
    if tables.ruled("terminal-ess-est", context.latin):
        return False
    match = ESS.search(context.latin)
    if match is None:
        return False
    shape = ("See", "Tea") if match.group(1) == "est" else ("See",)
    offset = _offset(match, letters)
    if not _ends(letters, offset, *shape):
        return False
    index = _vowel_at(letters, offset, len(shape))
    if index is None or not _reducible(letters, index):
        return False
    return letters[index].name == "It"


def undecided_y(context: Context, letters: Letters, tables: Tables) -> bool:
    """An unstressed full ·Eat at a terminal -y, where nothing in the IPA decides it.

    ReadLex writes the reduced terminal as happY `i` and keeps a full `iː` for one it
    thinks unreduced — but it marks no stress inside an unhyphenated compound, so
    carefree's ·Eat and algae's are the same shape segment for segment with opposite
    readings. Read's own discriminator is the stress, and it is exactly what is missing,
    so which of the two this is gets ruled on in rule-words.tsv rather than guessed.

    Behind a plural -s the same ·Eat asks `_y_plural`'s question as well, apogees
    against theses, and that is ruled on in the same table and counted in the same
    residue: every unstressed ·Eat this terminal owns is decided by hand.
    """
    if tables.ruled("terminal-y", context.latin):
        return False
    found = terminal_for(context)
    if found is None or found[0].id != "terminal-y":
        return False
    match = found[1]
    index = _vowel_at(letters, _offset(match, letters), 0)
    if index is None:
        return False
    return not letters[index].stressed and letters[index].name == "Eat"


def undecided_ful(context: Context, letters: Letters, tables: Tables) -> bool:
    """A -ful rewrite where ReadLex's vowel contradicts the POS the Manual keys on."""
    if tables.ruled("terminal-ful", context.latin):
        return False
    match = FUL.search(context.latin)
    if match is None:
        return False
    return apply_ful(context, letters, match) != letters


def undecided_ligature(context: Context, tables: Tables) -> str:
    """Why the mechanical alignment declined, for the validator's residue report."""
    latin = context.latin
    if "x" not in latin or tables.ligature_for(latin) is not None:
        return ""
    if latin.count("x") > 1:
        return "multiple-x"
    if len(_pairs(naive(context))) > 1:
        return "unaligned"
    return ""


def _gated(rule: Rule | Terminal, context: Context, tables: Tables) -> bool:
    """Whether a hand ruling stops this rule from running on this word."""
    return rule.id in GATED_RULES and tables.skipped(rule.id, context.latin)


def _stack(element: Element, tables: Tables) -> tuple[Letters, tuple[str, ...]]:
    context = element.context
    letters = element.letters
    applied: list[str] = []
    for rule in WORD_RULES:
        if _gated(rule, context, tables):
            continue
        after = rule.apply(context, letters)
        if after != letters:
            applied.append(rule.id)
            letters = after
    found = terminal_for(context)
    if found is None:
        return letters, tuple(applied)
    terminal, match = found
    if _gated(terminal, context, tables):
        return letters, tuple(applied)
    after = terminal.apply(context, letters, match)
    if after != letters:
        applied.append(terminal.id)
        letters = after
    return letters, tuple(applied)


def spell(context: Context, tables: Tables = NO_TABLES) -> Spelling:
    out: list[Letter] = []
    fired: set[str] = set()
    rulings: set[tuple[str, str]] = set()
    parts = split(context, naive(context))
    for element in parts:
        if not element.word:
            out.extend(element.letters)
            continue
        after, applied = _stack(element, tables)
        out.extend(after)
        fired.update(applied)
        rulings.update(tables.consulted(applied, element.context.latin))
    letters = tuple(out)
    senior, junior, signed, consulted = apply_signs(
        context.latin, context.pos, letters, tables.signs
    )
    lig = ligate(context, senior, tables)
    return Spelling(
        senior=render(senior),
        junior="" if names(junior) == names(senior) else render(junior),
        ligature="" if lig is None or names(lig) == names(senior) else render(lig),
        applied=tuple(rule.id for rule in RULES if rule.id in fired),
        ruled=tuple(sorted(rulings)),
        signed=signed,
        signs=consulted,
        elements=parts,
    )
