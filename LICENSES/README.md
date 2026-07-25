# Verbatim licence texts

`LICENSE.md` describes the licensing *structure*. The two licences it applies must also be
present here **verbatim**, because a paraphrased or reconstructed licence text is not the licence
and can change what is granted.

The required files are present and pinned to the publisher bytes retrieved on 2026-07-25:

| File | Canonical source | SHA-256 |
|---|---|---|
| `PolyForm-Noncommercial-1.0.0.md` | [PolyForm's versioned publisher repository](https://github.com/polyformproject/polyform-licenses/blob/1.0.0/PolyForm-Noncommercial-1.0.0.md) | `c0ea4a896d2c8c394b29f9427589996db826cd501c512279ff0ed3ef48fabbe5` |
| `CC-BY-NC-SA-4.0.md` | <https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode.txt> | `e66c269d4819aaab34b49ef5220c4ddab6756f21bb5180761a4eb8561f2b7bbd` |

To refresh them, fetch the exact publisher files; never reconstruct legal text from memory:

    curl -fsSL https://raw.githubusercontent.com/polyformproject/polyform-licenses/1.0.0/PolyForm-Noncommercial-1.0.0.md \
      -o LICENSES/PolyForm-Noncommercial-1.0.0.md
    curl -fsSL https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode.txt \
      -o LICENSES/CC-BY-NC-SA-4.0.md

Then update the pinned hashes only after comparing the bytes with the publisher source.

`verification/review_findings.py` check `L1` verifies both exact SHA-256 values. Presence or file
length alone is not accepted.
