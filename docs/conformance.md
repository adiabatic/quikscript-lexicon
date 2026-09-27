# What we conform to

This page lists the conventions that this project follows but does not set. Quikscript text has to follow them for other software to read it. The layers that depend on them link here instead of restating them.

## The PUA block

Quikscript is written in the Private Use Area, **U+E650–U+E67E**, one codepoint per letter, per the [quikscript.net CSUR proposal][csur]. Without a Quikscript font, every QS column renders as blank boxes. The `letters` key of [`lexicon/quikscript-lexicon.json`](../lexicon/quikscript-lexicon.json) names each codepoint, so the text can be read without one. [`src/qslex/csur.py`](../src/qslex/csur.py) holds the letter-to-codepoint table. The build derives the `letters` key from it, and the mapping loader checks every row’s letter names, codepoints and PUA string against it.

That range is the assignment the Quikscript community uses, but the Evertype CSUR index still lists it as *unassigned*. The authority for it is the proposal, not a registration.

## The language tag

Tag Quikscript text `en-Qaas`, per [quikscript.net/on-the-web](https://www.quikscript.net/on-the-web/). The Hunspell files `en-Qaas.dic` and `en-Qaas.aff` are named for it.

[csur]: https://www.quikscript.net/csur/
