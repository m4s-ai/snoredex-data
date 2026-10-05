"""Check the owner batch against its retained pre-intake PR head."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
before = json.loads(subprocess.check_output(['git', 'show', 'ba97d92cd51bcb25fee02b6821e32eefd977f7e9:verification/specimens.json'], cwd=ROOT))
after = json.loads((ROOT / 'verification/specimens.json').read_text(encoding='utf-8'))
old = {s['specimenId']: s for s in before['specimens']}
new = {s['specimenId']: s for s in after['specimens']}
expected = {'SPEC-0559':'non-holo', 'SPEC-0167':'holo', 'SPEC-0564':'non-holo', 'SPEC-0169':'holo', 'SPEC-0558':'non-holo', 'SPEC-0178':'non-holo', 'SPEC-0179':'non-holo', 'SPEC-0562':'reverse-holo', 'SPEC-0561':'non-holo', 'SPEC-0183':'holo', 'SPEC-0608':'non-holo', 'SPEC-0609':'holo'}
for sid, specimen in old.items():
    if sid not in expected:
        assert specimen == new[sid], sid
    else:
        for field in ('photograph', 'photographSha256', 'photographSource', 'recordedAt', 'heldBy', 'listingUrl'):
            assert specimen.get(field) == new[sid].get(field), (sid, field)
for sid, finish in expected.items():
    obs = new[sid]['physicalObservation']
    assert obs['finish'] == finish and obs['ownerAttestedFields'] == ['finish'], sid
    assert obs['ownerAttestedAt'] == '2026-10-05', sid
assert set(new) - set(old) == {'SPEC-0608', 'SPEC-0609'}
print('12 finish determinations accepted; all previous photo hashes/dates/provenance and unrelated specimens preserved')
