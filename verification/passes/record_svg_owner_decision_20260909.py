"""Record the owner's explicit SVG Traditional Chinese absence decision."""
import json
from correct_flf80_build_a_bear_20260902 import remove_establishing_ref
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
V = ROOT / 'verification'
def retire_source_first(graph, evidence):
    print_id = 'TW:SVG:021/049:base'
    claim_id = 'CLAIM:source-first:' + print_id
    source_id = 'SET-SRC-SF-6943573B2C9E'
    release_id = 'RELEASE:TW:T-Chinese:SVG:021/049:Snorlax-Unfazed-Fat-Thumping-Snore'
    removed_ids = {claim_id, release_id, 'LOCALSET:TW:SVG', 'EDITION:TW:T-Chinese:SVG',
                   'ASSERT:same-work:U0467:' + print_id,
                   'RARITYCLAIM:issue263:SVG:021/049:Snorlax-Unfazed-Fat-Thumping-Snore'}
    path = V / 'source_first_prints.json'
    document = json.loads(path.read_text(encoding='utf-8'))
    prior = [r for r in document['prints'] if r['printId'] == print_id]
    if prior:
        observation = {'unitId': 'U0467', 'at': '2026-09-09', 'status': 'contradicted',
                       'source': 'Owner attestation (domain expert)', 'evidence': evidence,
                       'supersededSourceFirstRecord': prior[0],
                       'supersededGraphEntities': [e for e in graph['entities'] if e['entityId'] in removed_ids]}
        with (V / 'evidence.jsonl').open('a', encoding='utf-8', newline='\n') as handle:
            handle.write(json.dumps(observation, ensure_ascii=False) + '\n')
    document['prints'] = [r for r in document['prints'] if r['printId'] != print_id]
    document['meta']['counts']['admitted'] = len(document['prints'])
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    graph['entities'] = [e for e in graph['entities'] if e['entityId'] not in removed_ids]
    graph['edges'] = [e for e in graph['edges'] if e['fromId'] not in removed_ids and e['toId'] not in removed_ids]
    for entity in graph['entities']:
        payload = entity['payload']
        if entity['entityType'] == 'set-source-disposition' and entity['entityId'] == source_id:
            payload.update(disposition='bounded-contradicted', targetRef=None, reason=evidence)
        if entity['entityId'] == 'CLAIM:legacy:U0467':
            payload['proposedTargetId'] = None
    graph['migrationDispositions'] = [r for r in graph['migrationDispositions']
        if not (r['sourceKind'] == 'source-first-record' and r['sourceId'] == print_id)]
    # Keep the issue question accounted for, with no positive counterpart mapping.
    for row in graph['migrationDispositions']:
        if row['sourceKind'] == 'legacy-issue-rekey' and row['sourceId'] == 'U0467':
            row.update(disposition='needs-positive-local-identity', targetRef=None, targetRefs=[], reason='issue #263 re-key')
        if row['sourceKind'] == 'set-catalogue-source' and row['sourceId'] == source_id:
            row.update(disposition='bounded-contradicted', targetRef=None, reason=evidence)
        if row['sourceKind'] == 'legacy-cardmarket-product' and release_id in row.get('targetRefs', []):
            row['targetRefs'] = [ref for ref in row['targetRefs'] if ref != release_id]
            row['targetRef'] = row['targetRefs'][0] if row['targetRefs'] else None
            row['reason'] = f"{len(row['targetRefs'])} established language-bearing card release(s)"
    for entity in graph['entities']:
        if entity['entityType'] == 'legacy-cardmarket-product':
            payload = entity['payload']
            payload['cardReleaseIds'] = [ref for ref in payload.get('cardReleaseIds', []) if ref != release_id]
    path = V / 'legacy_issue_rekeys.json'
    rekeys = json.loads(path.read_text(encoding='utf-8'))
    for question in rekeys['questionSets']:
        question['mappings'] = [r for r in question['mappings'] if r.get('sourceFirstRecordId') != print_id]
    path.write_text(json.dumps(rekeys, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    # Recompute product references using the remaining confirmed language claims.
    import sys
    sys.path.insert(0, str(ROOT / 'scripts'))
    from authoritative_graph import project_physical_evidence
    project_physical_evidence(graph)

def main():
    path = V / 'units.json'
    units = json.loads(path.read_text(encoding='utf-8'))
    unit = next(r for r in units if r['unitId'] == 'U0467')
    journal = V / 'evidence.jsonl'
    before = dict(unit)
    evidence = 'On 2026-09-09 the collection owner explicitly decided that SVG 021/049 has no Traditional Chinese variant: "hiermit entscheide ich das es keine t-chinese variante gibt". This supersedes the earlier repository confirmation. The absence decision belongs to the owner, not to 52Poke or Bulbapedia; earlier source evidence remains in the journal.'
    if unit.get('providerId') != 'owner-attestation':
        with journal.open('a',encoding='utf-8', newline='\n') as f:
            f.write(json.dumps({'unitId':'U0467','recordedAt':'2026-09-09','source':before.get('sourceUrl'),'status':before['status'],'evidence':before['evidence'],'supersededObservation':before},ensure_ascii=False)+'\n')
            f.write(json.dumps({'unitId':'U0467','at':'2026-09-09','source':'Owner attestation (domain expert)','status':'contradicted','evidence':evidence},ensure_ascii=False)+'\n')
    unit.update(status='contradicted',providerId='owner-attestation',sourceUrl=None,sourceRef=None,sourceType='Collection owner attestation (not-printed adjudication)',corroborated=False,evidence=evidence,checkedAt='2026-09-09T00:00:00',evidenceGranularity='specimen-or-card',evidenceIncludesCardList=False)
    path.write_text(json.dumps(units,ensure_ascii=False,indent=2)+'\n',encoding='utf-8', newline='\n')
    dataset_path = ROOT / 'snorlax_cards.json'
    dataset = json.loads(dataset_path.read_text(encoding='utf-8'))
    dataset['meta']['verification'].update({
        'confirmed': sum(r['status'] == 'confirmed' for r in units),
        'contradicted': sum(r['status'] == 'contradicted' for r in units),
        'needsManualReview': sum(r['status'] == 'needs-manual-review' for r in units),
        'open': sum(r['status'] == 'pending' for r in units),
        'totalUnits': len(units), 'lastUpdated': '2026-09-09',
    })
    dataset_path.write_text(json.dumps(dataset,ensure_ascii=False,indent=2)+'\n',encoding='utf-8', newline='\n')
    p=V/'owner_adjudications.json';d=json.loads(p.read_text(encoding='utf-8'))
    decision = {'adjudicationId': 'OA-20260909-U0467', 'unitId': 'U0467',
                'decision': 'not-printed', 'authority': 'collection-owner',
                'basis': 'multi-source-adjudication', 'decidedAt': '2026-09-09',
                'rationale': evidence,
                'evidenceRefs': ['https://github.com/m4s-ai/snoredex-data/issues/263', 'unit:U0467']}
    d['decisions'] = [r for r in d['decisions'] if r['unitId'] != 'U0467'] + [decision]
    d['meta']['generated'] = '2026-09-09'
    p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8', newline='\n')
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
    graph['edges'] = [e for e in graph['edges'] if not (
        e['fromType'] == 'candidate-claim' and e['fromId'] == claim_id and e['relation'] == 'materializes')]
    migration = next(r for r in graph['migrationDispositions']
                     if r['sourceKind'] == 'legacy-language-unit' and r['sourceId'] == 'U0467')
    migration.update(disposition='bounded-contradicted', targetRef=None, reason=evidence)
    retire_source_first(graph, evidence)
    graph['summary']['edges'] = len(graph['edges'])
    p.write_text(json.dumps(graph,ensure_ascii=False,indent=2)+'\n',encoding='utf-8', newline='\n')
if __name__=='__main__': main()

