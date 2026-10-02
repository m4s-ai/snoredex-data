"""Admit the owner-supplied 30thC photograph, without listing or launch-date claims."""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from admit_issue257_simplified_chinese_20260827 import upsert_entity, upsert_edge, upsert_migration

V = ROOT / 'verification'
DATE = '2026-10-01'
CODE = '30thC'
PID = 'CN:30thC:095/103:base'
# Preserve allocated graph IDs when correcting the printed code of the same photographed card.
RID = 'RELEASE:CN:S-Chinese:30th C:095/103:Snorlax-Good-Sleep-Collapse'
SID = 'SET-SRC-CN-30TH-C-095-20261001'
URL = 'https://i.ebayimg.com/images/g/RlwAAeSwjuhqumG-/s-l1600.png'
ORIGIN = 'reviewed-30th-cn-20261001'
BUNDLE = 'verification/evidence/30th-cn-20261001'
EVIDENCE = ('Owner-supplied photograph SPEC-0600, with original holder and listing unknown, visibly identifies Simplified Chinese 卡比兽, '
            '30thC 095/103 C, HP160, 安眠, the 130-damage sleep attack, Aya Kusube, regulation J '
            'and the yellow Pikachu 30th anniversary logo. Matching printed rules and illustration '
            'establish Snorlax-Good-Sleep-Collapse. Holographic reflection is visible on the physical card. '
            'Owner states this release is already released; no exact launch date, foil-pattern taxonomy '
            'or complete finish inventory is asserted.')

def read(name):
    return json.loads((V / name).read_text(encoding='utf-8'))

def write(name, data):
    (V / name).write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')

def main():
    graph = read('authoritative_graph.json')
    existing = {(e['entityType'],e['entityId']):copy.deepcopy(e) for e in graph['entities'] if e.get('origin')!=ORIGIN}
    prints = read('source_first_prints.json')
    sources = read('set_catalogue_sources.json')
    rarity = read('rarity_catalogue.json')
    specimens = read('specimens.json')
    specimen = next(s for s in specimens['specimens'] if s['specimenId']=='SPEC-0600')
    assert specimen['setCode'] in ('30th C', CODE)
    specimen['setCode'] = CODE
    specimen['heldBy'] = 'not established; image supplied by collection owner'
    specimen['inspectedFrom'] = 'Retained owner-supplied image; original holder and marketplace listing unknown'
    specimen['citedBy'] = [PID if ref=='CN:30th C:095/103:base' else ref for ref in specimen['citedBy']]
    specimen['observed'] = specimen['observed'].replace('30th C 095/103', '30thC 095/103')
    graph['migrationDispositions'] = [r for r in graph['migrationDispositions'] if not (r['sourceKind']=='source-first-record' and r['sourceId']=='CN:30th C:095/103:base')]
    row = dict(printId=PID,locality='CN',localSetCode=CODE,localNumber='095/103',language='S-Chinese',
               script='Hans',name='卡比兽',cardName='Snorlax',specimenId='SPEC-0600',
               providerId='inspected-specimen',sourceUrl=URL,cardImageUrl=URL,retrievedAt=DATE,
               releaseDate=None,releaseDatePrecision=None,releaseApproximate=False,
               releaseStatus='released',artist='Aya Kusube',variant='base',catchUpOf=None,
               corroborated=False,markAssetUrl=None,evidence=EVIDENCE,work='Snorlax-Good-Sleep-Collapse',
               raritySourceUrl=None,rarityProviderId='owner-attestation',rarityRetrievedAt=DATE)
    prints['prints'] = sorted([r for r in prints['prints'] if r['printId'] not in (PID,'CN:30th C:095/103:base')]+[row],key=lambda r:r['printId'])
    prints['meta']['counts']['admitted']=len(prints['prints'])
    profile = dict(sourceRecordId=SID,sourceKind='source-first-local-set-profile',provider='inspected-specimen',
                   providerRecordKey=PID,retrieved=DATE,sourceUrl=URL,
                   raw=dict(localCode=CODE,localName='30th Celebration',locality='CN',languages=['S-Chinese'],
                            scripts=['Hans'],printIds=[PID],providers=['inspected-specimen'],sourceUrls=[URL],
                            printedSetSize=103,printedSetSizeBasis='denominator printed on retained SPEC-0600',
                            observedCollectorNumbers=['095/103'],observedCoverage='one owner-supplied photograph; holder and listing unknown; not a complete inventory',
                            cardImageUrls=[URL],specimenId='SPEC-0600',printedRarity='C'))
    owner_sid=SID+'-OWNER-RARITY'
    owner=copy.deepcopy(profile)
    owner.update(sourceRecordId=owner_sid,provider='owner-attestation',providerRecordKey=PID+':owner-rarity',sourceUrl=None)
    owner['raw'].update(providers=['owner-attestation'],sourceUrls=[],rarity='Common',assertedBy='collection owner',
                        assertedAt=DATE,statement='für alle asiatischen sprachen übernehme das japanisch wenn noch offen',
                        basis='Owner explicitly extends Japanese M6a Common classification to Asian 30th counterparts; SPEC-0600 establishes exact CN identity and visible printed C.',
                        evidenceRefs=[BUNDLE+'/sources.json','verification/evidence/30th-owner-20261001/owner-determination.json'])
    replacements = {r['sourceRecordId']: r for r in [profile, owner]}
    existing_ids = {r['sourceRecordId'] for r in sources['sourceRecords']}
    sources['sourceRecords'] = [replacements.get(r['sourceRecordId'], r)
                                for r in sources['sourceRecords']]
    sources['sourceRecords'].extend(r for r in [profile, owner]
                                    if r['sourceRecordId'] not in existing_ids)
    def entity(kind,identity,payload):
        upsert_entity(graph,kind,identity,payload,origin=ORIGIN)
    local='LOCALSET:CN:30th%20C'
    edition='EDITION:CN:S-Chinese:30th C'
    template=next(e['payload'] for e in graph['entities'] if e['entityType']=='set-edition' and e['entityId']=='EDITION:TW:T-Chinese:M6a F')
    payload=copy.deepcopy(template)
    claim='CLAIM:source-first:CN:30th C:095/103:base'
    payload['setEditionId']=edition
    for part in ['identity','catalogue']:
        payload[part].update(setEditionId=edition,locality='CN',language='S-Chinese',script='Hans',localizationId='LOCALIZATION:CN:zh-Hans')
    payload['identity'].update(localSetCode=CODE,establishingClaimIds=[claim])
    payload['catalogue'].update(localSetId=local,localCode=CODE,establishingEvidenceIds=[SID])
    entity('local-set',local,dict(localSetId=local,locality='CN',localCode=CODE,observedNames=['30th Celebration'],productKind='physical-card-set-or-product',sourceRecordIds=[SID,owner_sid]))
    entity('set-edition',edition,payload)
    upsert_edge(graph,'set-edition',edition,'belongs-to','local-set',local)
    upsert_edge(graph,'set-edition',edition,'localized-as','localization','LOCALIZATION:CN:zh-Hans',{'reviewedAt':DATE,'basis':'Simplified Chinese card text in SPEC-0600'})
    for source in [profile,owner]:
        sid=source['sourceRecordId']
        entity('set-source-record',sid,source)
        disposition=dict(sourceRecordId=sid,disposition='mapped',targetRef=local,reason='Exact photographed 30thC localized identity and field-specific owner rarity determination.')
        entity('set-source-disposition',sid,disposition)
        upsert_edge(graph,'set-source-disposition',sid,'disposes','set-source-record',sid)
        upsert_edge(graph,'local-set',local,'observed-by','set-source-record',sid)
        upsert_migration(graph,dict(sourceKind='set-catalogue-source',sourceId=sid,disposition='mapped',targetRef=local,reason=disposition['reason']))
    release=copy.deepcopy(next(e['payload'] for e in graph['entities'] if e['entityType']=='card-release' and e['payload'].get('sourceFirstRecordIds')==['TW:M6a F:095/103:base']))
    release.update(cardReleaseId=RID,setEditionId=edition,locality='CN',language='S-Chinese',script='Hans',localSetCode=CODE,
                   claimIds=[claim],establishingClaimIds=[claim],sourceRecords=[URL],sourceFirstRecordIds=[PID],
                   releaseDate=None,releaseDatePrecision=None,releaseApproximate=False,releaseStatus='released')
    entity('card-release',RID,release)
    entity('candidate-claim',claim,dict(claimId=claim,claimKind='card-release',sourceKind='source-first-record',sourceId=PID,
           sourceRecord=URL,retrievedAt=DATE,evidenceStatus='confirmed',disposition='established-and-mapped',proposedTargetId=RID,materializedTargetId=RID,reason=EVIDENCE))
    upsert_migration(graph,dict(sourceKind='source-first-record',sourceId=PID,disposition='established-and-mapped',targetRef=RID,reason=EVIDENCE))
    upsert_edge(graph,'candidate-claim',claim,'materializes','card-release',RID)
    upsert_edge(graph,'card-release',RID,'belongs-to','set-edition',edition)
    upsert_edge(graph,'card-release',RID,'implements','work','WORK:Snorlax-Good-Sleep-Collapse',dict(assertionId='ASSERT:30th-same-work:cn',assertionType='same-work-decision',fromId=RID,toId='WORK:Snorlax-Good-Sleep-Collapse',sourceFirstRecordId=PID,assertedBy='repository source and image review',assertedAt=DATE,evidenceUrl=URL,evidence=EVIDENCE,destructiveMergeAllowed=False))
    entity('catalogue-card-release-ref',RID,dict(cardReleaseId=RID,setEditionId=edition,collectorNumber='095/103',origin=ORIGIN))
    upsert_edge(graph,'catalogue-card-release-ref',RID,'belongs-to','set-edition',edition)
    upsert_edge(graph,'catalogue-card-release-ref',RID,'references','card-release',RID)
    rc='RARITYCLAIM:owner:CN:30th C:095/103:base:20261001'
    entity('rarity-claim',rc,dict(rarityClaimId=rc,cardReleaseId=RID,sourceRecordId=owner_sid,sourceProvider='owner-attestation',
           sourceVocabulary='owner-classification',sourceNativeValue='Common',normalizedRarityId='common',sourceProductKey=PID+':owner-rarity',retrievedAt=DATE,evidence=owner['raw']['basis']))
    upsert_edge(graph,'rarity-claim',rc,'asserts-rarity-for','card-release',RID)
    upsert_edge(graph,'rarity-claim',rc,'observed-by','set-source-record',owner_sid)
    if not any(m['locality']=='CN' and m['sourceVocabulary']=='owner-classification' for m in rarity['sourceNativeMappings']):
        rarity['sourceNativeMappings'].append(dict(locality='CN',sourceVocabulary='owner-classification',basis='Explicit owner Common classification for identified Asian 30th counterparts; not a generic inference.',values={'Common':'common'}))
    sources['meta']['counts']['sourceRecords']=len(sources['sourceRecords'])
    sources['meta']['counts']['sourceFirstLocalSets']=sum(r['sourceKind']=='source-first-local-set-profile' for r in sources['sourceRecords'])
    after = {(e['entityType'],e['entityId']):e for e in graph['entities']}
    assert all(after[key]==value for key,value in existing.items()), 'Admission must preserve every existing graph entity'
    for name,data in [('authoritative_graph.json',graph),('source_first_prints.json',prints),('set_catalogue_sources.json',sources),('rarity_catalogue.json',rarity),('specimens.json',specimens)]:write(name,data)
    print('Admitted CN:30thC:095/103:base via SPEC-0600; exact release date remains unknown')

if __name__=='__main__':main()
