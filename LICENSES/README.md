# Verbatim licence texts

`LICENSE.md` describes the licensing *structure*. The two licences it applies must also be
present here **verbatim**, because a paraphrased or reconstructed licence text is not the licence
and can change what is granted.

Two files are required and are currently **missing**:

| File | Canonical source |
|---|---|
| `PolyForm-Noncommercial-1.0.0.md` | <https://polyformproject.org/licenses/noncommercial/1.0.0/> |
| `CC-BY-NC-SA-4.0.md` | <https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode.txt> |

They were not added automatically: the environment this repository was last worked in denies
outbound access to both hosts, and reproducing a legal text from memory risks silent divergence
from the published wording. Fetch them from the canonical URLs above and commit them unmodified.

    curl -fsSL https://polyformproject.org/licenses/noncommercial/1.0.0/ \
      -o LICENSES/PolyForm-Noncommercial-1.0.0.md
    curl -fsSL https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode.txt \
      -o LICENSES/CC-BY-NC-SA-4.0.md

Then verify each against the publisher's page before relying on it.

`verification/review_findings.py` fails check `L1` while either file is absent, and the release
gate refuses to publish, so this cannot be forgotten on the way to going public.
