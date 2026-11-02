<!-- doc: role=retained evidence for issue 438, Spanish Diamond & Pearl checklist re-read and owner decision; stage=history -->

> Historical record — 2026-11-02; current values are determined by canonical stores.

# #438 — Spanish Diamond & Pearl 37: no reverse holo

[`record_es_dp37_no_reverse_20261102.py`](../../passes/record_es_dp37_no_reverse_20261102.py) writes the data changes.

## What was wrong

The Spanish reverse holo of DP 37 had been confirmed from the official Spanish Diamond & Pearl checklist with a reading copied from the English one ("Standard Set … Parallel Set"). The Spanish PDF has no Parallel Set legend. It says **"Cartas 18-119: aparecen en una versión no foil."** By contrast, the English, German, French and Italian checklists all list a foil and a non-foil version for cards 18-119. [`excerpts.json`](excerpts.json) keeps the legends and the SHA-256 of each PDF.

All 82 localized checklists behind finish rows (DE/ES/FR/IT, 2026-11-02) were re-read. Every other one carries the legend its rows rely on: either the "Set paralelo / Parallelset / set parallèle / set parallelo" box or the "foil and non-foil version" sentence. The Lost Origin PDFs are images, and the Spanish one was checked visually. Spanish DP was the only mismatch.

## Owner decision

The owner: "Dann recherchiere weiter ob du irgendwo bestätigung dafür findest, wenn nicht setzen wir es auf grund dieser informationen auf not printed als reverse holo".

No confirmation of a Spanish reverse holo was found. Every source checked points the other way:

- the official Spanish checklist (non-foil only for cards 18-119);
- Bulbapedia's Diamond & Pearl page (revision 4590179, Spanish and Portuguese without reverse holos);
- Quuador's sets-and-languages list;
- dromanyte on Elite Fourum, thread 48558 post 9: "The sets that lacked RH variants in Spanish/Portuguese are: DP Base Set …".

The list is therefore closed at non-holo, with reverse holo rejected (`OAF-20261102-DP-37-es`).
