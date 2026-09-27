"""Latin text to Quikscript, ported from ReadLex’s latin2shaw.py.

The design is upstream’s: spaCy tokenization, Penn tags derived from C5 for heteronyms, dictionary lookup in the converter table, and affix fallbacks for words the lexicon lacks. The lookup values and the letter classes are changed for Quikscript. docs/latin2qs.md lists the differences from upstream.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import smartypants
import spacy
import unidecode
from spacy.matcher import PhraseMatcher
from spacy.tokenizer import Tokenizer
from spacy.tokens import Doc, Span, Token
from spacy.util import (
    compile_infix_regex,
    compile_prefix_regex,
    compile_suffix_regex,
    filter_spans,
)

from qslex.converter import converter, load_penn
from qslex.csur import CODEPOINT_OF
from qslex.letters import parse, render_qs
from qslex.readlex import repo_root
from qslex.words import load_contractions

LEXICON_JSON = "quikscript-lexicon.json"

SENIOR_COLUMN = "qs"
JUNIOR_COLUMN = "qs_junior"
X_COLUMN = "qs_x"

NAMER_DOT = "·"
CONSTRUCTED = "⚠️"
UNMATCHED = "✢"
APOSTROPHE = "’"

# The Manual’s angled parentheses, at the codepoints the CSUR proposal’s punctuation rows give them.
PARENTHESES = {"(": "\ue66e", ")": "\ue66f"}


def _qs(*names: str) -> str:
    return "".join(chr(CODEPOINT_OF[name]) for name in names)


# Letter classes that decide how 's and a constructed -s are voiced. After a sibilant, -s is a bare ·Zoo with no vowel before it (Jones's = ·Jay·Owe·No·Zoo·Zoo). After a voiceless letter, -s is ·See. After anything else, vowels included, it is ·Zoo.
SIBILANTS = frozenset(_qs(n) for n in ("See", "Zoo", "She", "J’ai", "Cheer", "Jay"))
VOICELESS = frozenset(
    _qs(n) for n in ("Pea", "Tea", "Key", "Fee", "Thaw", "See", "She", "Cheer", "Loch")
)
ZOO = _qs("Zoo")
SEE = _qs("See")

Rows = list[dict[str, str]]


def _s_suffix(last: str) -> str:
    if last in SIBILANTS:
        return ZOO
    if last in VOICELESS:
        return SEE
    return ZOO


# Spellings for the halves of a contraction that the tokenizer has split. Some opening halves have no lexicon entry (ca, sha). Others have an entry for a different word (ai) or with a different pronunciation (the verb do is ·Day·Ooze). The phrase list matches every straight-apostrophe contraction whole, so in practice only the HTML path uses the opening halves. That path does not run _plain’s unidecode, so a typographic apostrophe stays and splits don’t into do and n’t. The clitics keep or drop the apostrophe as the Manual does: n't attaches solid, and the rest keep it (docs/word-signs.md, “Contractions, possessives, and the apostrophe”). The two clitic rows in contractions.tsv, n't and 'll, are read from that file instead of being repeated here.
CONTRACTION_START = {
    "ai": _qs("Eight"),
    "ca": _qs("Key", "Ah"),
    "do": _qs("Day", "Owe"),
    "does": _qs("Day", "Utter", "Zoo"),
    "did": _qs("Day", "It", "Day"),
    "sha": _qs("She", "Ah"),
    "wo": _qs("Way", "Owe"),
}
CONTRACTION_END = {
    "'ve": APOSTROPHE + _qs("Vie"),
    "'m": APOSTROPHE + _qs("May"),
    "'d": APOSTROPHE + _qs("Day"),
    "'re": APOSTROPHE + _qs("Utter", "Roe"),
}

# Words whose pronunciation changes before “to”: have and has when “have to” means must, and the -sed verbs when tagged past tense or past participle.
HAVE_TO = {
    "have": _qs("He", "At", "Fee"),
    "has": _qs("He", "At", "See"),
}
VBD_TO = {
    "used": _qs("Ye", "Ooze", "See", "Tea"),
    "unused": _qs("Utter", "No", "Ye", "Ooze", "See", "Tea"),
    "supposed": _qs("See", "Utter", "Pea", "Owe", "See", "Tea"),
}
BEFORE_TO = HAVE_TO | VBD_TO

# The Manual keeps the apostrophe in spoken contractions (they'll = ·They·Eight’·Low in the Junior Bo-peep). When a word ends in one of these clitics and its dictionary spelling ends in the clitic’s letters, the apostrophe is put back before those letters. Verbal 's and n't attach solid and are left as the dictionary spells them.
CLITIC_LETTERS = {
    "'d": _qs("Day"),
    "'ll": _qs("Low"),
    "'m": _qs("May"),
    "'ve": _qs("Vie"),
    "'re": _qs("Utter", "Roe"),
}

# The Manual’s Quikscript text uses only single curly quotes, so the double quotes smartypants educates are changed to singles after it runs.
QUOTES = {"&#8220;": "&#8216;", "&#8221;": "&#8217;"}

ORDINAL = re.compile(r"([0-9]+)(st|nd|rd|th|s)")
ORDINAL_SUFFIXES = {
    "st": _qs("See", "Tea"),
    "nd": _qs("No", "Day"),
    "rd": _qs("Roe", "Day"),
    "th": _qs("Thaw"),
    "s": _qs("Zoo"),
}

# Common prefixes and suffixes of new coinings, spelled by the Manual’s affix conventions instead of being transliterated from upstream’s Shavian strings. tests/test_latin2qs.py checks some of them against the spelling the lexicon uses inside real words. The productive de-, pre-, pro- and re- take the full stressed vowel of a new coining. The prefix rules’ reduced vowel is for the lexicalized Latinate stems they were written for. The o'er row never spells the bare word, which is in the lexicon. It is used for the o'er… compounds, which nothing else builds.
PREFIXES: dict[str, str] = {
    "anti": _qs("At", "No", "Tea", "It"),
    "counter": _qs("Key", "Out", "No", "Tea", "Utter", "Roe"),
    "de": _qs("Day", "Eat"),
    "dis": _qs("Day", "It", "See"),
    "hyper": _qs("He", "I", "Pea", "Utter", "Roe"),
    "hypo": _qs("He", "I", "Pea", "Owe"),
    "mega": _qs("May", "Et", "Gay", "Utter"),
    "meta": _qs("May", "Et", "Tea", "Utter"),
    "micro": _qs("May", "I", "Key", "Roe", "Owe"),
    "multi": _qs("May", "Utter", "Low", "Tea", "It"),
    "mis": _qs("May", "It", "See"),
    "neuro": _qs("No", "Ye", "Ooze", "Utter", "Roe", "Owe"),
    "non": _qs("No", "Ox", "No"),
    "o'er": _qs("Owe", "Utter", "Roe"),
    "out": _qs("Out", "Tea"),
    "over": _qs("Owe", "Vie", "Utter", "Roe"),
    "poly": _qs("Pea", "Ox", "Low", "It"),
    "post": _qs("Pea", "Owe", "See", "Tea"),
    "pre": _qs("Pea", "Roe", "Eat"),
    "pro": _qs("Pea", "Roe", "Owe"),
    "pseudo": _qs("See", "Ye", "Ooze", "Day", "Owe"),
    "re": _qs("Roe", "Eat"),
    "sub": _qs("See", "Utter", "Bay"),
    "super": _qs("See", "Ooze", "Pea", "Utter", "Roe"),
    "ultra": _qs("Utter", "Low", "Tea", "Roe", "Utter"),
    "un": _qs("Utter", "No"),
    "under": _qs("Utter", "No", "Day", "Utter", "Roe"),
}
# -ness and -less take ·Et, which the Manual uses to distinguish them from the -us, -ous terminal. A direct transliteration of upstream’s Shavian strings would give them ·Utter. Upstream put -esque in its prefixes dict, where startswith() can never match it. Here it is a suffix.
SUFFIXES: dict[str, str] = {
    "able": _qs("Utter", "Bay", "Low"),
    "bound": _qs("Bay", "Out", "No", "Day"),
    "esque": _qs("Et", "See", "Key"),
    "ful": _qs("Fee", "Utter", "Low"),
    "hood": _qs("He", "Foot", "Day"),
    "ish": _qs("It", "She"),
    "ism": _qs("It", "Zoo", "Utter", "May"),
    "less": _qs("Low", "Et", "See"),
    "like": _qs("Low", "I", "Key"),
    "ness": _qs("No", "Et", "See"),
}
# The Manual’s terminal -ful depends on the part of speech: the noun mouthful keeps ·Foot, and the adjective careful reduces it to ·Utter.
FUL_NOUN = _qs("Fee", "Foot", "Low")

NAMER_DOT_ENTS = frozenset(
    {"PERSON", "FAC", "ORG", "GPE", "LOC", "PRODUCT", "EVENT", "WORK_OF_ART", "LAW"}
)

TITLES = frozenset(
    {
        "archbishop",
        "archdeacon",
        "baron",
        "baroness",
        "bishop",
        "captain",
        "count",
        "countess",
        "cpt",
        "dame",
        "deacon",
        "doctor",
        "dr.",
        "dr",
        "duchess",
        "duke",
        "earl",
        "emperor",
        "empress",
        "gov.",
        "gov",
        "governor",
        "justice",
        "king",
        "lady",
        "lord",
        "marchioness",
        "marquess",
        "marquis",
        "miss",
        "missus",
        "mister",
        "mistress",
        "mr.",
        "mr",
        "mrs.",
        "mrs",
        "ms.",
        "ms",
        "mx.",
        "mx",
        "pope",
        "pres.",
        "pres",
        "president",
        "prince",
        "princess",
        "prof.",
        "prof",
        "professor",
        "queen",
        "rev.",
        "rev",
        "reverend",
        "saint",
        "sen.",
        "sen",
        "senator",
        "sir",
        "st.",
        "st",
        "viscount",
        "viscountess",
    }
)

STYLE = r"(<style\b[^>]*>.*?</style>)"
SCRIPT = r"(<script\b[^>]*>.*?</script>)"
TAG = r"(?!(?:<style[^>]*?>.*?</style>|<script[^>]*?>.*?</script>))(<.*?>)"
HTML_PATTERNS = f"{STYLE}|{SCRIPT}|{TAG}"


@dataclass(frozen=True)
class Options:
    """The grade, and the two Senior facilities whose defaults it sets.

    Senior uses the X-letters and the §III contractions by default. Junior uses neither. The grade sets these defaults but does not forbid either facility. The Manual’s Note on p.25 calls the Sections II and III facilities impossible as a first stage in children’s writing. That is advice about teaching children to write, and it does not limit what a converter may produce. So every combination of grade and facilities is allowed, and Junior with a facility turned on is spelled instead of refused.

    `x_letters` and `contractions` accept `None`, which means “use the grade’s default”. After construction both are plain booleans, so later code does not need to know how they were set.
    """

    junior: bool = False
    x_letters: bool | None = None
    contractions: bool | None = None

    def __post_init__(self) -> None:
        senior = not self.junior
        if self.x_letters is None:
            object.__setattr__(self, "x_letters", senior)
        if self.contractions is None:
            object.__setattr__(self, "contractions", senior)


def _contraction_qs(spelling: str) -> str:
    return render_qs(parse(spelling))


def _educated(text: str) -> str:
    result: str = smartypants.smartypants(text)
    for double, single in QUOTES.items():
        result = result.replace(double, single)
    return result


def _apostrophized(lower: str, spelling: str) -> str:
    if lower.startswith("'"):
        return APOSTROPHE + spelling
    for clitic, letters in CLITIC_LETTERS.items():
        if lower.endswith(clitic) and spelling.endswith(letters):
            return spelling[: -len(letters)] + APOSTROPHE + letters
    return spelling


class Transliterator:
    """The spaCy pipeline and the lookup tables, loaded once and reused.

    The converter table (Latin word to tagged spellings) is rebuilt here from the lexicon JSON instead of being read from a file of its own. It contains nothing the lexicon JSON does not. Its Penn tags are the lexicon’s C5 tags mapped through `c5-to-penn.tsv`, which this module also uses to tag the contractions. A separate file would duplicate that data. Building the table at startup takes a fraction of a second.
    """

    def __init__(self, lexicon: Path | None = None) -> None:
        lexicon = lexicon if lexicon is not None else repo_root() / "lexicon"
        master = json.loads((lexicon / LEXICON_JSON).read_text(encoding="utf-8"))
        penn = load_penn()
        self.rows_of: dict[str, Rows] = converter(
            (
                (
                    entry["Latn"],
                    entry["pos"],
                    entry["qs"],
                    entry.get("qs_junior", ""),
                    entry.get("qs_x", ""),
                )
                for group in master["entries"].values()
                for entry in group
            ),
            penn,
        )
        phrases = master["phrases"]

        self.contraction_words: dict[tuple[str, str], str] = {}
        self.contraction_end: dict[str, str] = dict(CONTRACTION_END)
        for entry in load_contractions():
            if not entry.written:
                continue
            spelling = _contraction_qs(entry.contraction)
            if entry.kind == "clitic":
                self.contraction_end[entry.word] = spelling
            else:
                tag = penn[entry.pos].penn if entry.pos else ""
                self.contraction_words[(entry.word, tag)] = spelling

        self.letter_spellings: dict[str, str] = {
            letter: self._letter_row(letter)
            for letter in "abcdefghijklmnopqrstuvwxyz"
            if letter in self.rows_of
        }

        self.nlp = spacy.load("en_core_web_sm", exclude=["parser", "lemmatizer"])
        tokenizer = self.nlp.tokenizer
        assert isinstance(tokenizer, Tokenizer)
        prefixes = list(self.nlp.Defaults.prefixes or []) + [r"""^[-–—]+"""]
        tokenizer.prefix_search = compile_prefix_regex(prefixes).search
        infixes = list(self.nlp.Defaults.infixes or []) + [
            r"""[.,?!:;\-–—"~\(\)\[\]]+"""
        ]
        tokenizer.infix_finditer = compile_infix_regex(infixes).finditer
        suffixes = list(self.nlp.Defaults.suffixes or []) + [r"""[-–—]+$"""]
        tokenizer.suffix_search = compile_suffix_regex(suffixes).search

        self.phrase_matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")
        self.phrase_matcher.add(
            "phrases", [self.nlp.make_doc(phrase) for phrase in phrases]
        )

    def _letter_row(self, letter: str) -> str:
        rows = self.rows_of[letter]
        for row in rows:
            if row["tag"] == "SYM":
                return row["qs"]
        return rows[-1]["qs"]

    def tokenize(self, text: str) -> Doc:
        doc = self.nlp(text)
        spans = [
            Span(doc, start, end, label=match_id)
            for match_id, start, end in self.phrase_matcher(doc)
        ]
        with doc.retokenize() as retokenizer:
            for span in filter_spans(spans):
                retokenizer.merge(span)

        new_ents: list[Span] = []
        for ent in doc.ents:
            if ent.label_ == "PERSON" and ent.start != 0:
                if doc[ent.start - 1].lower_ in TITLES:
                    new_ents.append(Span(doc, ent.start - 1, ent.end, label=ent.label))
                else:
                    new_ents.append(ent)
            elif ent.label_ in NAMER_DOT_ENTS:
                if doc[ent.start].lower_ == "the":
                    new_ents.append(Span(doc, ent.start + 1, ent.end, label=ent.label))
                else:
                    new_ents.append(ent)
            else:
                new_ents.append(ent)
        doc.ents = tuple(filter_spans(new_ents))
        return doc

    def _row_for(self, rows: Rows, tag: str) -> dict[str, str]:
        for row in rows:
            if row["tag"] == tag:
                return row
            if tag == "NNP" and row["tag"] == "NN":
                return row
            if tag == "NNPS" and row["tag"] == "NNS":
                return row
            # spaCy tags relative that as WDT, and no converter row has that tag. ReadLex tags it CJT, the conjunction, which c5-to-penn.tsv maps to IN.
            if tag == "WDT" and row["tag"] == "IN":
                return row
        return rows[-1]

    def _spelling(self, row: dict[str, str], options: Options) -> str:
        # No row has both qs_x and qs_junior. An X-letter needs an x in the word, and no word with a junior spelling has one. So the order of these two checks does not matter.
        if options.x_letters and (x_letter := row.get(X_COLUMN)):
            return x_letter
        if options.junior and (junior := row.get(JUNIOR_COLUMN)):
            return junior
        return row[SENIOR_COLUMN]

    def _fallback_spelling(self, word: str, options: Options) -> str | None:
        rows = self.rows_of.get(word)
        if rows is None:
            return None
        return self._spelling(rows[-1], options)

    def _dot(self, token: Token, spelling: str) -> str:
        if token.ent_iob_ == "B" and token.ent_type_ in NAMER_DOT_ENTS:
            return NAMER_DOT
        if self._is_initialism(token, spelling):
            return NAMER_DOT
        return ""

    def _is_initialism(self, token: Token, spelling: str) -> bool:
        lower = token.lower_
        if len(lower) < 2 or not lower.isalpha() or not token.text.isupper():
            return False
        try:
            letters = "".join(self.letter_spellings[c] for c in lower)
        except KeyError:
            return False
        return letters == spelling

    def _is_standalone_letter(self, token: Token) -> bool:
        lower = token.lower_
        if len(token.text) != 1 or not token.text.isalpha():
            return False
        if lower not in self.letter_spellings:
            return False
        if lower == "a" and token.tag_ == "DT":
            return False
        if lower == "i" and token.tag_ == "PRP":
            return False
        return not (lower == "o" and token.tag_ == "UH")

    def _contracted(self, token: Token) -> str | None:
        if token.ent_type_ in NAMER_DOT_ENTS or token.tag_ in ("NNP", "NNPS"):
            return None
        lower = token.lower_.replace(APOSTROPHE, "'")
        exact = self.contraction_words.get(
            (lower, token.tag_)
        ) or self.contraction_words.get((lower, ""))
        if exact is not None:
            return exact
        if lower.endswith("n't"):
            stem = self.contraction_words.get((lower[:-3], ""))
            if stem is not None:
                return stem + self.contraction_end["n't"]
        for clitic in ("'s", "'ll", "'d", "'re", "'ve", "'m"):
            if not lower.endswith(clitic):
                continue
            stem = self.contraction_words.get((lower[: -len(clitic)], ""))
            if stem is None:
                continue
            if clitic == "'s":
                return stem + _s_suffix(stem[-1])
            return stem + self.contraction_end[clitic]
        return None

    def convert(self, doc: Doc, options: Options) -> str:
        built = ""
        for token in doc:
            lower = token.lower_.replace(APOSTROPHE, "'")

            if options.contractions:
                contracted = self._contracted(token)
                if contracted is not None:
                    built += contracted + token.whitespace_
                    continue

            if (
                lower in CONTRACTION_START
                and token.i < len(doc) - 1
                and doc[token.i + 1].lower_.replace(APOSTROPHE, "'")
                in self.contraction_end
            ):
                built += CONTRACTION_START[lower]
            elif lower in self.contraction_end:
                built += self.contraction_end[lower] + token.whitespace_
            elif lower == "'s":
                suffix = _s_suffix(built[-1]) if built else ZOO
                built += suffix + token.whitespace_
            elif lower == "'" and token.tag_ == "POS":
                built += token.whitespace_
            elif (
                lower in BEFORE_TO
                and token.i < len(doc) - 1
                and (doc[token.i + 1].lower_ == "to")
            ):
                if (
                    lower in HAVE_TO
                    and token.i < len(doc) - 2
                    and doc[token.i + 2].tag_ in ("VB", "VBP")
                ):
                    built += HAVE_TO[lower] + token.whitespace_
                elif lower in VBD_TO and token.tag_ in ("VBD", "VBN"):
                    built += VBD_TO[lower] + token.whitespace_
                else:
                    built += self._converted_word(token, options)
            elif match := ORDINAL.fullmatch(lower):
                number, suffix = match.groups()
                built += number + ORDINAL_SUFFIXES[suffix] + token.whitespace_
            else:
                built += self._converted_word(token, options)
        return built

    def _converted_word(self, token: Token, options: Options) -> str:
        lower = token.lower_.replace(APOSTROPHE, "'")

        if self._is_standalone_letter(token):
            return NAMER_DOT + self.letter_spellings[token.lower_] + token.whitespace_

        rows = self.rows_of.get(lower)
        if rows is not None:
            spelling = self._spelling(self._row_for(rows, token.tag_), options)
            if "'" in lower:
                spelling = _apostrophized(lower, spelling)
            return self._dot(token, spelling) + spelling + token.whitespace_

        constructed = self._constructed(token, options)
        if constructed is not None:
            return constructed

        if token.text.isalpha():
            return token.text + UNMATCHED + token.whitespace_
        return "".join(PARENTHESES.get(c, c) for c in token.text) + token.whitespace_

    def _constructed(self, token: Token, options: Options) -> str | None:
        lower = token.lower_.replace(APOSTROPHE, "'")

        for affix, spelling in PREFIXES.items():
            if not lower.startswith(affix):
                continue
            rest = self._fallback_spelling(lower[len(affix) :], options)
            if rest is not None:
                dot = self._dot(token, rest)
                return dot + spelling + rest + CONSTRUCTED + token.whitespace_
        for affix, spelling in SUFFIXES.items():
            if not lower.endswith(affix):
                continue
            if affix == "ful" and token.tag_.startswith("NN"):
                spelling = FUL_NOUN
            rest = self._fallback_spelling(lower[: -len(affix)], options)
            if rest is not None:
                dot = self._dot(token, rest)
                return dot + rest + spelling + CONSTRUCTED + token.whitespace_

        if lower.endswith("s"):
            stem = self._fallback_spelling(lower[:-1], options)
            if stem is not None:
                dot = self._dot(token, stem)
                suffix = _s_suffix(stem[-1])
                return dot + stem + suffix + CONSTRUCTED + token.whitespace_
        return None

    def transliterate(self, text: str, options: Options | None = None) -> str:
        options = options if options is not None else Options()
        if text.strip().casefold().startswith("<!doctype html"):
            return self._html(text, options)
        return self._plain(text, options)

    def _html(self, text: str, options: Options) -> str:
        out = ""
        for part in re.split(HTML_PATTERNS, text, flags=re.DOTALL):
            if part is None:
                continue
            if any(
                re.fullmatch(pattern, part, flags=re.DOTALL)
                for pattern in (STYLE, SCRIPT, TAG)
            ):
                out += part
            else:
                out += self.convert(self.tokenize(part), options)
        return _educated(out)

    def _plain(self, text: str, options: Options) -> str:
        text = unidecode.unidecode(text)
        text = re.sub(r"(\S)(\[)", r"\1 \2", text)
        text = re.sub(r"](\S)", r"] \1", text)
        out = ""
        for line in text.splitlines():
            out += self.convert(self.tokenize(line), options) + "\n"
        return html.unescape(_educated(out))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Transliterate Latin-alphabet English text to Quikscript"
    )
    parser.add_argument("files", nargs="*", type=Path)
    grade = parser.add_mutually_exclusive_group()
    grade.add_argument(
        "--senior",
        dest="junior",
        action="store_false",
        default=None,
        help="Senior Quikscript: X-letters and the §III contractions, the default",
    )
    grade.add_argument(
        "--junior",
        dest="junior",
        action="store_true",
        default=None,
        help="Junior Quikscript: neither facility unless it is asked for",
    )
    parser.add_argument(
        "--x-letters",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="the ·Excite/·Exam X-letter spellings (senior takes them, junior does not)",
    )
    parser.add_argument(
        "--contractions",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="the Manual’s §III Senior contractions (senior takes them, junior does not)",
    )
    parser.add_argument("--lexicon", type=Path, default=None)
    args = parser.parse_args(argv)

    options = Options(
        junior=bool(args.junior),
        x_letters=args.x_letters,
        contractions=args.contractions,
    )
    transliterator = Transliterator(args.lexicon)
    if args.files:
        text = "\n".join(f.read_text(encoding="utf-8") for f in args.files)
    else:
        text = sys.stdin.read()
    sys.stdout.write(transliterator.transliterate(text, options))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
