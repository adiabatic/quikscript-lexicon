# What we conform to

The conventions this project does not get to decide. Nothing below is a choice the lexicon makes; it is what Quikscript text has to be for anything else to read it, held in one place so the layers that depend on it can point at it rather than restate it.

## The PUA block

Quikscript is written in the Private Use Area, **U+E650–U+E67E**, one codepoint per letter, per the [quikscript.net CSUR proposal][csur]. Without a Quikscript font every QS column renders as blank boxes; the `letters` key of [`lexicon/quikscript-lexicon.json`](../lexicon/quikscript-lexicon.json) names each codepoint so the text can be read without one. [`src/qslex/csur.py`](../src/qslex/csur.py) is that table as the repo holds it — the shipped `letters` key is derived from it, and the mapping loader self-verifies letters ↔ codepoints ↔ PUA agreement against it.

Worth stating honestly: that range is the de-facto community assignment, but the live Evertype CSUR index still lists it as *unassigned*. The authority here is the proposal, not a registration.

## The language tag

Tag Quikscript text `en-Qaas`, per [quikscript.net/on-the-web](https://www.quikscript.net/on-the-web/). The shipped Hunspell pair, `en-Qaas.dic` and `en-Qaas.aff`, is named for it.

[csur]: https://www.quikscript.net/csur/
