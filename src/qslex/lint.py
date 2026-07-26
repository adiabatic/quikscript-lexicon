from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from qslex.elements import DIVIDERS, components, elements
from qslex.letters import VOWELS, Letters, names, parse
from qslex.rules import AL, ALLY, ENT, ING_TAILS, Tables
from qslex.tables import rows_of

PRAGMAS_FILE = "lint-pragmas.tsv"
PRAGMAS_HEADER = ["check", "word", "reason", "note"]

# The one reason a word is allowed to break a check: a defect recorded against another
# issue, not a licence. Any other reason is a bare exception, which is what this table
# exists to prevent.
DEFECT = "known-defect"

REDUCIBLE = frozenset({"It", "Utter"})
VOWEL_CHARS = frozenset("ɪieæaɑɒɔʊuʌəɜːƏIÆⱭ")
STRESS_MARKS = frozenset("ˈˌ")
LIGATURES = frozenset({"Excite", "Exam"})

# "While L needs no preceding vowel in Spaniel, one is clearly needed wherever -al
# follows on a vowel-sound" — so ·Ye counts here as the vowel it stands in for.
VOWELS_BEFORE_L = VOWELS | {"Ye"}

# The Manual's own trigger for each check, as an Orthodox ending. Latin-gating is the
# whole difference between a check that re-derives a rule and one that re-reports the
# corpus: ·Et·No·Tea is only wrong where Orthodox spells -ent, and ReadLex's own /e/
# elsewhere is not this project's business. A check whose rule keys on the same ending
# takes that rule's own pattern — `rules.ENT`, `rules.AL`, and `rules.ALLY`, which
# claims -able and -ally before -al does. The two written out here are the ones that
# differ, because -men is the exception the -land rule carves out.
LAND = re.compile(r"(?<=.)(land|ment|man)(s)?$")
MEN = re.compile(r"(?<=.)men$")


@dataclass(frozen=True)
class Site:
    """One element of one entry, as the lint sees it."""

    word: str
    latin: str
    letters: Letters
    ligature: Letters
    ipa: str
    last: bool

    @property
    def spelt(self) -> tuple[str, ...]:
        return names(self.letters)

    @property
    def ligated(self) -> tuple[str, ...]:
        return names(self.ligature or self.letters)

    @property
    def stressed(self) -> bool:
        return bool(self.ipa) and self.ipa[0] in STRESS_MARKS

    @property
    def reducible_ending(self) -> bool:
        """Whether the last vowel ReadLex wrote for this element is a schwa.

        Every rule these checks re-derive is conditioned on an *unstressed* vowel, and
        the only vowel ReadLex writes that is unstressed by definition is ə. ɪ and ʌ are
        syllable nuclei as often as not — distil, fulfil, until — so reading them as
        reducible is what turns a rule into a false alarm.
        """
        vowels = [c for c in self.ipa if c in VOWEL_CHARS]
        return bool(vowels) and vowels[-1] in {"ə", "Ə"}


@dataclass(frozen=True)
class Check:
    id: str
    requires: str
    test: Callable[[Site, Tables], str]


def _tail(site: Site, *shape: str) -> bool:
    return site.spelt[-len(shape) :] == shape


def _before(spelt: tuple[str, ...], shape: tuple[str, ...]) -> str:
    return spelt[-len(shape) - 1] if len(spelt) > len(shape) else ""


def _ing_affix(latin: str) -> str:
    for tail in ING_TAILS:
        if latin.endswith(tail) and latin.rindex("ing") > 0:
            return tail
    return ""


ING_SHAPES = {
    "ing": ("Oolong",),
    "ings": ("Oolong", "Zoo"),
    "ingly": ("Oolong", "Low", "It"),
    "ingness": ("Oolong", "No", "Et", "See"),
}


def ing_vowel_omitted(site: Site, tables: Tables) -> str:
    """ "Provided it is an affix and not a root, omit vowel-i." (terminal-ing)

    "Spell -ing in full after roots ending in -y: ·Key·At·Roe·It·It·Oolong = carrying."
    A root ending in -i is the same case — taxi, ski — and is skipped with it.
    """
    affix = _ing_affix(site.latin)
    stem = site.latin[: site.latin.rindex("ing")] if affix else ""
    if not affix or stem.endswith(("y", "i")):
        return ""
    if tables.ruled("terminal-ing", site.latin):
        return ""
    shape = ING_SHAPES[affix]
    if not _tail(site, *shape):
        return ""
    return "·It before the -ing" if _before(site.spelt, shape) == "It" else ""


def al_vowel_omitted(site: Site, tables: Tables) -> str:
    """ "omit any unstressed vowel sound between L and the preceding consonant"

    Entry-final elements only: "Where another syllable is added, the vowel sound before
    this L must be clearly pronounced and spelt" — and a following element adds a
    syllable exactly as a suffix does. (terminal-al-el-le-il)
    """
    if not site.last or not AL.search(site.latin) or ALLY.search(site.latin):
        return ""
    if not site.reducible_ending:
        return ""
    spelt = site.spelt
    if spelt and spelt[-1] in {"Zoo", "See"} and site.latin.endswith("s"):
        spelt = spelt[:-1]
    if len(spelt) < 3 or spelt[-1] != "Low" or spelt[-2] not in REDUCIBLE:
        return ""
    if spelt[-3] in VOWELS_BEFORE_L:
        return ""
    return f"·{spelt[-2]} between a consonant and the final ·Low"


def ent_ance_utter(site: Site, tables: Tables) -> str:
    """ "written invariably with standard ·Utter·No" (terminal-ent-ance)"""
    match = ENT.search(site.latin)
    if not match or LAND.search(site.latin) or not site.reducible_ending:
        return ""
    shape = ("No", "Tea") if match.group(1) in {"ent", "ant"} else ("No", "See")
    if not _tail(site, *shape):
        return ""
    before = _before(site.spelt, shape)
    return f"·{before} before ·No, not ·Utter" if before not in {"Utter", ""} else ""


def land_ment_vowel_omitted(site: Site, tables: Tables) -> str:
    """ "The unstressed vowel is omitted for convenient joining except in -men."

    (terminal-land-ment)
    """
    match = LAND.search(site.latin)
    if not match or not site.reducible_ending:
        return ""
    ending = match.group(1)
    shape = {"land": ("No", "Day"), "ment": ("No", "Tea"), "man": ("No",)}[ending]
    consonant = {"land": "Low", "ment": "May", "man": "May"}[ending]
    if site.latin.endswith("s") and site.spelt[-1:] == ("Zoo",):
        spelt = site.spelt[:-1]
    else:
        spelt = site.spelt
    if spelt[-len(shape) :] != shape:
        return ""
    vowel = spelt[-len(shape) - 1] if len(spelt) > len(shape) else ""
    if vowel not in REDUCIBLE:
        return ""
    keeps = spelt[-len(shape) - 2] if len(spelt) > len(shape) + 1 else ""
    if keeps != consonant:
        return ""
    return f"·{vowel} kept between ·{consonant} and the -{ending}"


def men_keeps_a_vowel(site: Site, tables: Tables) -> str:
    """ "The unstressed vowel is omitted for convenient joining except in -men."

    The Manual says the vowel is kept, not which vowel it is, and ReadLex writes both:
    seamen ˈsiːmen gives ·May·Et·No, dutchmen ˈdʌtʃmən gives ·May·Utter·No. Either
    keeps seamen apart from seaman, which is what the exception is for; demanding ·Et
    would be inventing a sound the corpus does not record. (terminal-land-ment)
    """
    if not MEN.search(site.latin) or not _tail(site, "No"):
        return ""
    vowel = _before(site.spelt, ("No",))
    if not vowel or vowel in VOWELS:
        return ""
    return f"-men joined straight onto ·{vowel}, with no vowel kept"


def initial_ex_et(site: Site, tables: Tables) -> str:
    """ "·Et·Excite for Excite, Extreme, Expect, with an initial vowel ·Et easier than
    ·It." (section-2)
    """
    spelt = site.ligated
    if not site.latin.startswith("ex") or len(spelt) < 2:
        return ""
    if spelt[1] not in LIGATURES or site.stressed:
        return ""
    return f"·{spelt[0]} before the ligature, not ·Et" if spelt[0] != "Et" else ""


def ligature_only_with_x(site: Site, tables: Tables) -> str:
    """ "but only where Orthodox spells these sounds with X … and only one ·Excite in
    Xerxes." (section-2)
    """
    used = sum(1 for name in site.ligated if name in LIGATURES)
    available = site.latin.count("x")
    if used <= available:
        return ""
    return f"{used} ligatures for {available} x in the Latin"


CHECKS: tuple[Check, ...] = (
    Check(
        "terminal-ing-vowel-omitted",
        "an -ing affix is written ·Oolong with no ·It before it",
        ing_vowel_omitted,
    ),
    Check(
        "terminal-al-vowel-omitted",
        "a final L drops the unstressed vowel before it, after a consonant",
        al_vowel_omitted,
    ),
    Check(
        "terminal-ent-ance-utter",
        "-ent, -ant, -ence and -ance are written invariably with ·Utter·No",
        ent_ance_utter,
    ),
    Check(
        "terminal-land-ment-vowel-omitted",
        "-land, -ment and -man omit the unstressed vowel",
        land_ment_vowel_omitted,
    ),
    Check(
        "terminal-men-keeps-a-vowel",
        "-men is the one ending that keeps its vowel",
        men_keeps_a_vowel,
    ),
    Check(
        "initial-ex-et",
        "an initial ex- takes ·Et before the ligature",
        initial_ex_et,
    ),
    Check(
        "x-ligature-only-with-x",
        "no more ligatures than the Latin has x",
        ligature_only_with_x,
    ),
)

CHECK_IDS = tuple(check.id for check in CHECKS)


def load_pragmas(path: Path | None = None) -> dict[tuple[str, str], str]:
    """The words a check is allowed to fire on, and why each is allowed.

    Every row records a defect and says what it is, so that the table cannot quietly
    become the bare exception list this project keeps refusing to write.
    """
    pragmas: dict[tuple[str, str], str] = {}
    for lineno, source, row in rows_of(path, PRAGMAS_FILE, PRAGMAS_HEADER):
        check, word, reason, note = row
        if check not in CHECK_IDS:
            raise ValueError(f"{source}:{lineno}: {check!r} is not a check")
        if reason != DEFECT:
            raise ValueError(
                f"{source}:{lineno}: reason must be {DEFECT!r}, got {reason!r}"
            )
        if not note:
            raise ValueError(
                f"{source}:{lineno}: a known defect needs a note saying what it is"
            )
        key = (check, word)
        if key in pragmas:
            raise ValueError(f"{source}:{lineno}: duplicate pragma for {key}")
        pragmas[key] = reason
    return pragmas


def _chunks(text: str) -> tuple[str, ...]:
    return tuple(re.split(r"[ -]", text))


def sites(word: str, spelling: str, ligature: str, ipa: str) -> tuple[Site, ...]:
    """One Site per element, cut where `qslex.elements` cuts.

    Where the Latin, the spelling and the IPA do not agree about how many pieces an
    entry has, the entry is treated as one element — the same conservatism that keeps
    to-day and dhs intact.
    """
    letters = parse(spelling)
    pairs = elements(word, letters)
    ligated = elements(word, parse(ligature)) if ligature else None
    ipa_parts = _chunks(ipa)
    if pairs is None:
        return (Site(word, word, letters, parse(ligature), ipa, True),)
    words = [part for part in components(word) if part not in DIVIDERS]
    runs = [run for part, run in pairs if part not in DIVIDERS]
    ligature_runs = (
        [run for part, run in ligated if part not in DIVIDERS]
        if ligated is not None and len(ligated) == len(pairs)
        else [()] * len(runs)
    )
    chunks = ipa_parts if len(ipa_parts) == len(words) else [ipa] * len(words)
    return tuple(
        Site(word, latin, run, tuple(other), chunk, index == len(words) - 1)
        for index, (latin, run, other, chunk) in enumerate(
            zip(words, runs, ligature_runs, chunks, strict=True)
        )
    )


def lint(
    word: str,
    spelling: str,
    ligature: str,
    ipa: str,
    tables: Tables,
) -> tuple[tuple[str, str, str], ...]:
    """Every check this entry breaks, as (check id, element, what is wrong)."""
    out: list[tuple[str, str, str]] = []
    for site in sites(word, spelling, ligature, ipa):
        for check in CHECKS:
            complaint = check.test(site, tables)
            if complaint:
                out.append((check.id, site.latin, complaint))
    return tuple(out)
