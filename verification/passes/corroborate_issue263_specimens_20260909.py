"""Connect the reviewed issue-263 retailer/seller images to their exact print claims."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from source_registry import SPECIMEN_SOURCE_TYPES, provenance_url, specimen_provider


def main():
    directory = ROOT / 'verification'
    path = directory / 'source_first_prints.json'
    document = json.loads(path.read_text(encoding='utf-8'))
    prints = {row['printId']: row for row in document['prints']}
    specimens = json.loads((directory / 'specimens.json').read_text(encoding='utf-8'))['specimens']
    graph_path = directory / 'authoritative_graph.json'
    graph = json.loads(graph_path.read_text(encoding='utf-8'))
    releases = {e['entityId']: e['payload'] for e in graph['entities'] if e['entityType'] == 'card-release'}
    targets = {e['payload']['sourceId']: e['payload']['materializedTargetId']
               for e in graph['entities'] if e['entityType'] == 'candidate-claim'
               and e['payload']['sourceKind'] == 'source-first-record'}
    for specimen in specimens:
        if not 494 <= int(specimen['specimenId'].split('-')[1]) <= 506:
            continue
        source_type = SPECIMEN_SOURCE_TYPES[str(specimen['heldBy']).casefold()]
        urls = {provenance_url(specimen.get(key)) for key in ('listingUrl', 'photographSource')} - {None}
        for print_id in specimen.get('citedBy') or []:
            row = prints[print_id]
            providers = {specimen_provider(url, source_type) for url in urls}
            independent = providers & {'retailer-listing', 'seller-listing-photo'} - {row['providerId']}
            if not independent:
                continue  # The unknown origin of SPEC-0505 cannot establish a second provider.
            before = dict(row)
            row['corroborated'] = True
            row['corroboratingSourceUrls'] = sorted(set(row.get('corroboratingSourceUrls') or []) | urls)
            row['corroboratingSpecimenIds'] = sorted(set(row.get('corroboratingSpecimenIds') or []) | {specimen['specimenId']})
            release = releases[targets[print_id]]
            release['sourceRecords'] = sorted(set(release.get('sourceRecords') or []) | urls)
            if row != before:
                observation = {'sourceFirstRecordId': print_id, 'specimenId': specimen['specimenId'],
                    'at': '2026-09-09', 'status': 'confirmed', 'source': sorted(urls)[0], 'sourceUrls': sorted(urls),
                    'evidence': 'Previously inspected exact-card image corroborates identity from a second provider; finish observations remain separate.',
                    'supersededObservation': before}
                with (directory / 'evidence.jsonl').open('a', encoding='utf-8', newline='\n') as handle:
                    handle.write(json.dumps(observation, ensure_ascii=False) + '\n')
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    graph_path.write_text(json.dumps(graph, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
