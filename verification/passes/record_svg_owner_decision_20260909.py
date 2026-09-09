"""Record the owner's explicit SVG Traditional Chinese absence decision."""
import json
from correct_flf80_build_a_bear_20260902 import remove_establishing_ref
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
V = ROOT / 'verification'
def main():
    path = V / 'units.json'
    units = json.loads(path.read_text(encoding='utf-8'))
    unit = next(r for r in units if r['unitId'] == 'U0467')
    journal = V / 'evidence.jsonl'
    before = dict(unit)
    evidence = 'On 2026-09-09 the collection owner explicitly decided that SVG 021/049 has no Traditional Chinese variant: "hiermit entscheide ich das es keine t-chinese variante gibt". This supersedes the earlier repository confirmation. The absence decision belongs to the owner, not to 52Poke or Bulbapedia; earlier source evidence remains in the journal.'
    if unit.get('providerId') != 'owner-attestation':
        with journal.open('a',encoding='utf-8') as f:
            f.write(json.dumps({'unitId':'U0467','recordedAt':'2026-09-09','source':before.get('sourceUrl'),'status':before['status'],'evidence':before['evidence'],'supersededObservation':before},ensure_ascii=False)+'\n')
            f.write(json.dumps({'unitId':'U0467','at':'2026-09-09','source':'Owner attestation (domain expert)','status':'contradicted','evidence':evidence},ensure_ascii=False)+'\n')
    unit.update(status='contradicted',providerId='owner-attestation',sourceUrl=None,sourceRef=None,sourceType='Collection owner attestation (not-printed adjudication)',corroborated=False,evidence=evidence,checkedAt='2026-09-09T00:00:00',evidenceGranularity='specimen-or-card',evidenceIncludesCardList=False)
    path.write_text(json.dumps(units,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    dataset_path = ROOT / 'snorlax_cards.json'
    dataset = json.loads(dataset_path.read_text(encoding='utf-8'))
    dataset['meta']['verification'].update({
        'confirmed': sum(r['status'] == 'confirmed' for r in units),
        'contradicted': sum(r['status'] == 'contradicted' for r in units),
        'needsManualReview': sum(r['status'] == 'needs-manual-review' for r in units),
        'open': sum(r['status'] == 'pending' for r in units),
        'totalUnits': len(units), 'lastUpdated': '2026-09-09',
    })
    dataset_path.write_text(json.dumps(dataset,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    p=V/'owner_adjudications.json';d=json.loads(p.read_text(encoding='utf-8'))
    decision = {'adjudicationId': 'OA-20260909-U0467', 'unitId': 'U0467',
                'decision': 'not-printed', 'authority': 'collection-owner',
                'basis': 'multi-source-adjudication', 'decidedAt': '2026-09-09',
                'rationale': evidence,
                'evidenceRefs': ['https://github.com/m4s-ai/snoredex-data/issues/263', 'unit:U0467']}
    d['decisions'] = [r for r in d['decisions'] if r['unitId'] != 'U0467'] + [decision]
    d['meta']['generated'] = '2026-09-09'
    p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    p = V / 'authoritative_graph.json'
    graph = json.loads(p.read_text(encoding='utf-8'))
    claim_id = 'CLAIM:legacy:U0467'
    claim = next(e['payload'] for e in graph['entities']
                 if e['entityType'] == 'candidate-claim' and e['entityId'] == claim_id)
    target = claim['proposedTargetId']
    claim.update(sourceRecord=None, evidenceStatus='contradicted',
                 disposition='bounded-contradicted', materializedTargetId=None,
                 reason=evidence)
    remove_establishing_ref(graph['entities'], claim_id)
    release = next(e['payload'] for e in graph['entities']
                   if e['entityType'] == 'card-release' and e['entityId'] == target)
    release['nonEstablishingClaimIds'] = sorted(set(release.get('nonEstablishingClaimIds', []) + [claim_id]))
    graph['edges'] = [e for e in graph['edges'] if not (
        e['fromType'] == 'candidate-claim' and e['fromId'] == claim_id and e['relation'] == 'materializes')]
    migration = next(r for r in graph['migrationDispositions']
                     if r['sourceKind'] == 'legacy-language-unit' and r['sourceId'] == 'U0467')
    migration.update(disposition='bounded-contradicted', targetRef=None, reason=evidence)
    graph['summary']['edges'] = len(graph['edges'])
    p.write_text(json.dumps(graph,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__': main()

