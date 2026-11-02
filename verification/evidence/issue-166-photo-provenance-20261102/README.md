<!-- doc: role=retained photo provenance repair; stage=history -->

> Historical record — 2026-11-02; current values are determined by canonical stores.

# Issue 166 original-photo provenance

Five existing photographs, SPEC-0028 through SPEC-0032, were retained on 2026-08-10 but still named former temporary local files as their provenance. The exact original attachment UUIDs and the owner's original comment in issue 166 identify their sources. Each original was retrieved again through GitHub's signed image candidate and compared byte-for-byte with the retained canonical photograph: all five SHA-256 hashes match.

`provenance-manifest.json` records the stable original attachment and comment URLs, retained paths and hashes. Signed transport URLs and the full issue HTML are intentionally not retained. GitHub TLS retrieval used the operating system trust store because the Python process lacked the relevant certificate chain; certificate validation was not disabled.

The existing importer direct mode updates only the photograph source relationship using the unchanged local original. SPEC IDs, image bytes/hashes, inspection dates, ownership, observations, citations and physical properties are conserved. No card, finish, edition or source admission is inferred from this provenance repair. The standing photo inbox still has zero unprocessed original attachments.
