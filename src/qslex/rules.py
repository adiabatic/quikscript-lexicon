from __future__ import annotations

import csv
import dataclasses
import re
from collections.abc import Callable, Container
from dataclasses import dataclass, field
from pathlib import Path

from qslex.letters import Letter, Letters, names, parse, render, unknown_names
from qslex.mapping import open_data
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
}

LIGATURES_FILE = "x-ligatures.tsv"
LIGATURES_HEADER = ["word", "pos", "ligature", "reason", "note"]
LIGATURE_REASONS = {"multiple-x", "unaligned"}

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
ING_TAILS = ("ingness", "ingly", "ings", "ing")


@dataclass(frozen=True)
class Context:
    latin: str
    pos: str
    ipa: str
    tokens: tuple[Token, ...]


@dataclass(frozen=True)
class Spelling:
    senior: str
    junior: str
    ligature: str
    applied: tuple[str, ...]
    signed: tuple[str, ...]
    signs: tuple[tuple[str, str], ...]


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


def _reducible(letters: Letters, index: int) -> bool:
    return not letters[index].stressed and letters[index].name in REDUCIBLE


def _force(letters: Letters, offset: int, shape: tuple[str, ...], want: str) -> Letters:
    """Normalise the vowel that precedes `shape` at the end of the word."""
    if not _ends(letters, offset, *shape):
        return letters
    index = _vowel_at(letters, offset, len(shape))
    if index is None or not _reducible(letters, index):
        return letters
    return _rename(letters, index, want)


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
    pos: str
    ligature: str
    reason: str
    note: str


@dataclass(frozen=True)
class Tables:
    words: dict[tuple[str, str], RuleWord] = field(default_factory=dict)
    ligatures: dict[tuple[str, str], LigatureRule] = field(default_factory=dict)
    signs: Signs = field(default_factory=dict)

    def skipped(self, rule: str, latin: str) -> bool:
        entry = self.words.get((rule, latin))
        return entry is not None and entry.decision == "skip"

    def ruled(self, rule: str, latin: str) -> bool:
        return (rule, latin) in self.words

    def ligature_for(self, latin: str, pos: str) -> LigatureRule | None:
        return self.ligatures.get((latin, pos)) or self.ligatures.get((latin, ""))


NO_TABLES = Tables()


def load_rule_words(path: Path | None = None) -> dict[tuple[str, str], RuleWord]:
    known: dict[tuple[str, str], RuleWord] = {}
    with open_data(path, RULE_WORDS_FILE) as (f, source):
        reader = csv.reader(f, delimiter="\t")
        header = next(reader)
        if header != RULE_WORDS_HEADER:
            raise ValueError(f"unexpected header in {source}: {header}")
        for lineno, row in enumerate(reader, start=2):
            if len(row) != len(RULE_WORDS_HEADER):
                raise ValueError(
                    f"{source}:{lineno}: expected {len(RULE_WORDS_HEADER)} fields, "
                    f"got {len(row)}"
                )
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


def load_x_ligatures(path: Path | None = None) -> dict[tuple[str, str], LigatureRule]:
    known: dict[tuple[str, str], LigatureRule] = {}
    with open_data(path, LIGATURES_FILE) as (f, source):
        reader = csv.reader(f, delimiter="\t")
        header = next(reader)
        if header != LIGATURES_HEADER:
            raise ValueError(f"unexpected header in {source}: {header}")
        for lineno, row in enumerate(reader, start=2):
            if len(row) != len(LIGATURES_HEADER):
                raise ValueError(
                    f"{source}:{lineno}: expected {len(LIGATURES_HEADER)} fields, "
                    f"got {len(row)}"
                )
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
            key = (rule.word, rule.pos)
            if key in known:
                raise ValueError(f"{source}:{lineno}: duplicate row for {key}")
            known[key] = rule
    return known


def load_tables() -> Tables:
    return Tables(load_rule_words(), load_x_ligatures(), load_word_signs())


def apply_es_ed(context: Context, letters: Letters, tables: Tables) -> Letters:
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


def apply_con_com(context: Context, letters: Letters, tables: Tables) -> Letters:
    latin = context.latin
    if len(latin) < 5 or not latin.startswith(("con", "com")):
        return letters
    consonant = "May" if latin[2] == "m" else "No"
    if not _ends(letters[:3], 0, "Key", "Utter", consonant):
        return letters
    if letters[1].stressed:
        return letters
    return _drop(letters, 1)


def _prefix(
    context: Context,
    letters: Letters,
    prefixes: tuple[str, ...],
    index: int,
    want: str,
    frame: tuple[tuple[int, str], ...],
) -> Letters:
    """Normalise the prefix vowel at `index`, once `frame` confirms the consonants."""
    latin = context.latin
    if not latin.startswith(prefixes) or len(latin) < len(prefixes[0]) + 3:
        return letters
    if len(letters) <= max(index, *(at for at, _ in frame)):
        return letters
    if any(letters[at].name != name for at, name in frame):
        return letters
    if not letters[index].is_vowel or not _reducible(letters, index):
        return letters
    return _rename(letters, index, want)


def apply_un(context: Context, letters: Letters, tables: Tables) -> Letters:
    return _prefix(context, letters, ("un",), 0, "Utter", ((1, "No"),))


def apply_an_al_ar(context: Context, letters: Letters, tables: Tables) -> Letters:
    for prefix, consonant in (("an", "No"), ("al", "Low"), ("ar", "Roe")):
        if context.latin.startswith(prefix):
            return _prefix(context, letters, (prefix,), 0, "Utter", ((1, consonant),))
    return letters


def apply_ob_of(context: Context, letters: Letters, tables: Tables) -> Letters:
    for prefix, consonant in (("ob", "Bay"), ("of", "Fee")):
        if context.latin.startswith(prefix):
            return _prefix(context, letters, (prefix,), 0, "Utter", ((1, consonant),))
    return letters


def apply_be_de_re(context: Context, letters: Letters, tables: Tables) -> Letters:
    if tables.skipped("prefix-be-de-re", context.latin):
        return letters
    for prefix, consonant in (("be", "Bay"), ("de", "Day"), ("re", "Roe")):
        if context.latin.startswith(prefix):
            return _prefix(context, letters, (prefix,), 1, "It", ((0, consonant),))
    return letters


def apply_pre_pro(context: Context, letters: Letters, tables: Tables) -> Letters:
    if context.latin.startswith("pre"):
        return _prefix(context, letters, ("pre",), 2, "It", ((0, "Pea"), (1, "Roe")))
    if context.latin.startswith("pro"):
        return _prefix(context, letters, ("pro",), 2, "Utter", ((0, "Pea"), (1, "Roe")))
    return letters


def apply_per_pur(context: Context, letters: Letters, tables: Tables) -> Letters:
    return _prefix(
        context, letters, ("per", "pur"), 1, "Utter", ((0, "Pea"), (2, "Roe"))
    )


def apply_in_en(context: Context, letters: Letters, tables: Tables) -> Letters:
    return _prefix(context, letters, ("in", "en"), 0, "It", ((1, "No"),))


def _ing_stem(latin: str) -> str:
    return latin[: latin.rindex("ing")]


def apply_ing(context: Context, letters: Letters, tables: Tables) -> Letters:
    latin = context.latin
    if not latin.endswith(ING_TAILS) or "ing" not in latin[1:]:
        return letters
    if _ing_stem(latin).endswith("y"):
        return letters
    if tables.skipped("terminal-ing", latin):
        return letters
    for index in range(len(letters) - 2, 0, -1):
        if letters[index].name == "It" and letters[index + 1].name == "Oolong":
            return _drop(letters, index)
    return letters


def apply_ally(context: Context, letters: Letters, tables: Tables) -> Letters:
    match = ALLY.search(context.latin)
    if match is None:
        return letters
    offset = _offset(match, letters)
    if match.group(1) == "ally":
        if not _ends(letters, offset, "Low", "It"):
            return letters
        index = len(letters) - offset - 2
        if index and letters[index - 1].is_vowel:
            return _force(letters, offset, ("Low", "It"), "Utter")
        return _insert(letters, index, "Utter")
    tail = ("Low", "It") if match.group(1) in {"ably", "ibly"} else ("Low",)
    return _omit(letters, offset, tail)


def apply_tion(context: Context, letters: Letters, tables: Tables) -> Letters:
    match = TION.search(context.latin)
    if match is None:
        return letters
    return _omit(letters, _offset(match, letters), ("No",))


def apply_ess(context: Context, letters: Letters, tables: Tables) -> Letters:
    match = ESS.search(context.latin)
    if match is None or tables.skipped("terminal-ess-est", context.latin):
        return letters
    shape = ("See", "Tea") if match.group(1) == "est" else ("See",)
    return _force(letters, _offset(match, letters), shape, "Et")


def apply_land(context: Context, letters: Letters, tables: Tables) -> Letters:
    match = LAND.search(context.latin)
    if match is None or match.group(1) == "men":
        return letters
    offset = _offset(match, letters)
    for shape in (("No", "Day"), ("No", "Tea"), ("No",)):
        after = _omit(letters, offset, shape)
        if after != letters:
            return after
    return letters


def apply_ent(context: Context, letters: Letters, tables: Tables) -> Letters:
    match = ENT.search(context.latin)
    if match is None:
        return letters
    offset = _offset(match, letters)
    for shape in (("No", "Tea"), ("No", "See")):
        after = _force(letters, offset, shape, "Utter")
        if after != letters:
            return after
    return letters


def apply_ous(context: Context, letters: Letters, tables: Tables) -> Letters:
    match = OUS.search(context.latin)
    if match is None:
        return letters
    return _force(letters, _offset(match, letters), ("See",), "Utter")


def apply_er(context: Context, letters: Letters, tables: Tables) -> Letters:
    match = ER.search(context.latin)
    if match is None:
        return letters
    offset = _offset(match, letters)
    if not _ends(letters, offset, "Roe"):
        return letters
    index = _vowel_at(letters, offset, 1)
    if index is None or letters[index - 1].is_vowel:
        return letters
    return _force(letters, offset, ("Roe",), "Utter")


def apply_ier(context: Context, letters: Letters, tables: Tables) -> Letters:
    match = IER.search(context.latin)
    if match is None:
        return letters
    return _tighten(letters, _offset(match, letters), ("Utter", "Roe"))


def apply_ia(context: Context, letters: Letters, tables: Tables) -> Letters:
    match = IA.search(context.latin)
    if match is None:
        return letters
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


def apply_y(context: Context, letters: Letters, tables: Tables) -> Letters:
    match = YY.search(context.latin)
    if match is None:
        return letters
    if match.group(2) and match.group(1) == "e":
        # -es after a silent e is a plural, not the terminal -e of simile or coffee.
        return letters
    return _force(letters, _offset(match, letters), (), "It")


def apply_ain(context: Context, letters: Letters, tables: Tables) -> Letters:
    match = AIN.search(context.latin)
    if match is None:
        return letters
    return _force(letters, _offset(match, letters), ("No",), "Utter")


def apply_age(context: Context, letters: Letters, tables: Tables) -> Letters:
    latin = context.latin
    match = AGE.search(latin)
    if match is None:
        return letters
    stem = latin[: latin.rindex("age")]
    want = "It" if stem.endswith(("y", "i")) else "Utter"
    return _force(letters, _offset(match, letters), ("Jay",), want)


def apply_ward(context: Context, letters: Letters, tables: Tables) -> Letters:
    match = WARD.search(context.latin)
    if match is None:
        return letters
    offset = _offset(match, letters)
    if not _ends(letters, offset, "Way", "Utter", "Roe", "Day"):
        return letters
    index = len(letters) - offset - 3
    if letters[index].stressed:
        return letters
    return _drop(_drop(letters, index), index)


def apply_ful(context: Context, letters: Letters, tables: Tables) -> Letters:
    match = FUL.search(context.latin)
    if match is None or tables.skipped("terminal-ful", context.latin):
        return letters
    offset = _offset(match, letters)
    shape = ("Low", "It") if match.group(1) else ("Low",)
    if not _ends(letters, offset, *shape):
        return letters
    index = _vowel_at(letters, offset, len(shape))
    if index is None or index == 0 or letters[index - 1].name != "Fee":
        return letters
    if letters[index].stressed or letters[index].name not in {"Utter", "Foot"}:
        return letters
    return _rename(letters, index, "Foot" if context.pos.startswith("NN") else "Utter")


def apply_al(context: Context, letters: Letters, tables: Tables) -> Letters:
    match = AL.search(context.latin)
    if match is None:
        return letters
    return _omit(letters, _offset(match, letters), ("Low",))


def apply_en_on(context: Context, letters: Letters, tables: Tables) -> Letters:
    match = EN.search(context.latin)
    if match is None:
        return letters
    return _force(letters, _offset(match, letters), ("No",), "Utter")


Apply = Callable[[Context, Letters, "Tables"], Letters]


@dataclass(frozen=True)
class Rule:
    id: str
    stage: str
    apply: Apply
    latin: re.Pattern[str] | None = None


def _pattern(body: str) -> re.Pattern[str]:
    return re.compile(rf"(?<=.){body}")


ES_ED = _pattern(r"(es|ed)(s|ness|nesses|ly)?$")
ALLY = _pattern(r"(ally|ably|ibly|able|ible)(s)?$")
TION = _pattern(r"(ation|asion|ssion|shion|tion|cean|sion|gion)(s|es)?$")
ESS = _pattern(r"(ness|less|est|ess)(es)?$")
LAND = _pattern(r"(land|ment|man|men)(s)?$")
ENT = _pattern(r"(ence|ance|ent|ant)(s)?$")
OUS = _pattern(r"(scious|tious|cious|ous|us)(es)?$")
WARD = _pattern(r"ward(s)?$")
FUL = _pattern(r"ful(ly)?(s)?$")
AIN = _pattern(r"ain(s)?$")
AGE = _pattern(r"age(s)?$")
AL = _pattern(r"(al|el|le|il)(s)?$")
IA = _pattern(r"(ian|ean|ion|ia|ea)(s)?$")
IER = _pattern(r"(ier|ior)(s)?$")
ER = _pattern(r"(er|ar|ir|or|our|yr|re)(s)?$")
YY = _pattern(r"(ity|ily|ey|ie|y|e)(s)?$")
EN = _pattern(r"(en|on)(s)?$")

PREFIX_RULES: tuple[Rule, ...] = (
    Rule("prefix-con-com", "prefix", apply_con_com),
    Rule("prefix-un", "prefix", apply_un),
    Rule("prefix-an-al-ar", "prefix", apply_an_al_ar),
    Rule("prefix-ob-of", "prefix", apply_ob_of),
    Rule("prefix-be-de-re", "prefix", apply_be_de_re),
    Rule("prefix-pre-pro", "prefix", apply_pre_pro),
    Rule("prefix-per-pur", "prefix", apply_per_pur),
    Rule("prefix-in-en", "prefix", apply_in_en),
)

TERMINAL_RULES: tuple[Rule, ...] = (
    Rule("terminal-ally-able", "terminal", apply_ally, ALLY),
    Rule("terminal-tion", "terminal", apply_tion, TION),
    Rule("terminal-ess-est", "terminal", apply_ess, ESS),
    Rule("terminal-land-ment", "terminal", apply_land, LAND),
    Rule("terminal-ent-ance", "terminal", apply_ent, ENT),
    Rule("terminal-us-ous", "terminal", apply_ous, OUS),
    Rule("terminal-ward", "terminal", apply_ward, WARD),
    Rule("terminal-ful", "terminal", apply_ful, FUL),
    Rule("terminal-ain", "terminal", apply_ain, AIN),
    Rule("terminal-age", "terminal", apply_age, AGE),
    Rule("terminal-al-el-le-il", "terminal", apply_al, AL),
    Rule("terminal-ia-ea", "terminal", apply_ia, IA),
    Rule("terminal-ier-ior", "terminal", apply_ier, IER),
    Rule("terminal-er", "terminal", apply_er, ER),
    Rule("terminal-y", "terminal", apply_y, YY),
    Rule("terminal-en-on", "terminal", apply_en_on, EN),
)

RULES: tuple[Rule, ...] = (
    (
        Rule("terminal-es-ed", "epenthesis", apply_es_ed),
        Rule("terminal-ing", "affix", apply_ing),
    )
    + PREFIX_RULES
    + TERMINAL_RULES
)

RULE_IDS = tuple(rule.id for rule in RULES)


def claims(rule: Rule, context: Context) -> bool:
    """Whether this terminal rule owns the end of the word, fire or not."""
    return rule.latin is not None and rule.latin.search(context.latin) is not None


def terminal_for(context: Context) -> Rule | None:
    for rule in TERMINAL_RULES:
        if claims(rule, context):
            return rule
    return None


def _pairs(letters: Letters) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for index in range(len(letters) - 1):
        pair = (letters[index].name, letters[index + 1].name)
        if pair == ("Key", "See"):
            found.append((index, "Excite"))
        elif pair == ("Gay", "Zoo"):
            found.append((index, "Exam"))
    return found


def ligate(context: Context, letters: Letters, tables: Tables) -> Letters | None:
    latin = context.latin
    declared = tables.ligature_for(latin, context.pos)
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
    if not latin.endswith(ING_TAILS) or "ing" not in latin[1:]:
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
    return apply_be_de_re(context, letters, tables) != letters


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


def undecided_ful(context: Context, letters: Letters, tables: Tables) -> bool:
    """A -ful rewrite where ReadLex's vowel contradicts the POS the Manual keys on."""
    if tables.ruled("terminal-ful", context.latin):
        return False
    match = FUL.search(context.latin)
    if match is None:
        return False
    offset = _offset(match, letters)
    shape = ("Low", "It") if match.group(1) else ("Low",)
    if not _ends(letters, offset, *shape):
        return False
    index = _vowel_at(letters, offset, len(shape))
    if index is None or letters[index - 1].name != "Fee" or letters[index].stressed:
        return False
    if letters[index].name not in {"Utter", "Foot"}:
        return False
    want = "Foot" if context.pos.startswith("NN") else "Utter"
    return letters[index].name != want


def undecided_ligature(context: Context, letters: Letters, tables: Tables) -> str:
    """Why the mechanical alignment declined, for the validator's residue report."""
    latin = context.latin
    if "x" not in latin or tables.ligature_for(latin, context.pos) is not None:
        return ""
    if latin.count("x") > 1:
        return "multiple-x"
    if len(_pairs(letters)) > 1:
        return "unaligned"
    return ""


def spell(context: Context, tables: Tables = NO_TABLES) -> Spelling:
    letters = naive(context)
    applied: list[str] = []
    terminal = terminal_for(context)
    for rule in RULES:
        if rule.stage == "terminal" and rule is not terminal:
            continue
        after = rule.apply(context, letters, tables)
        if after != letters:
            applied.append(rule.id)
            letters = after
    senior, signed, consulted = apply_signs(
        context.latin, context.pos, letters, tables.signs, "senior"
    )
    junior, *_ = apply_signs(
        context.latin, context.pos, letters, tables.signs, "junior"
    )
    lig = ligate(context, senior, tables)
    return Spelling(
        senior=render(senior),
        junior="" if names(junior) == names(senior) else render(junior),
        ligature="" if lig is None or names(lig) == names(senior) else render(lig),
        applied=tuple(applied),
        signed=signed,
        signs=consulted,
    )
