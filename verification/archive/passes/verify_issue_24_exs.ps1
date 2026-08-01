$ErrorActionPreference = 'Stop'

$verificationDir = Split-Path -Parent $PSScriptRoot
$repoRoot = Split-Path -Parent $verificationDir
$unitsPath = Join-Path $verificationDir 'units.json'
$cardsPath = Join-Path $repoRoot 'snorlax_cards.json'
$evidencePath = Join-Path $verificationDir 'evidence.jsonl'
$statePath = Join-Path $verificationDir 'state.json'

$sourceUrl = 'https://bulbapedia.bulbagarden.net/wiki/Snorlax_(Wizards_Promo_49)'
$sourceType = 'Bulbapedia (fan wiki), card release history'
$evidenceText = 'The card article identifies Keita Takahashi as the illustrator and distinguishes two Japanese printings: the glossy Expansion Sheet 1 Sheet 16 printing with a rarity symbol, and the non-glossy Quick Starter Gift Set Red Deck reprint. It also records the extra CoroCoro Comic Illust Contest text on the Quick Starter printing.'
$checkedAt = Get-Date -Format s

$units = Get-Content $unitsPath -Raw -Encoding utf8 | ConvertFrom-Json
$targetUnits = @($units | Where-Object {
    $_.setCode -eq 'EXS' -and "$($_.number)" -eq '' -and
    $_.variant -eq 'base' -and $_.language -eq 'Japanese'
})
if ($targetUnits.Count -ne 1) {
    throw "Expected exactly one EXS Japanese language unit, found $($targetUnits.Count)."
}

$unit = $targetUnits[0]
$unit.status = 'confirmed'
$unit.sourceUrl = $sourceUrl
$unit.sourceType = $sourceType
$unit.evidence = $evidenceText
$unit.checkedAt = $checkedAt
$unit.artist = 'Keita Takahashi'
$units | ConvertTo-Json -Depth 6 | Set-Content $unitsPath -Encoding utf8NoBOM

$cardsDocument = Get-Content $cardsPath -Raw -Encoding utf8 | ConvertFrom-Json
$targetCards = @($cardsDocument.cards | Where-Object {
    $_.setCode -eq 'EXS' -and "$($_.number)" -eq '' -and -not $_.variantToken
})
if ($targetCards.Count -ne 1) {
    throw "Expected exactly one EXS Cardmarket product, found $($targetCards.Count)."
}

$card = $targetCards[0]
$card.artist = 'Keita Takahashi'
$card.artistSource = $sourceType
$card | Add-Member -NotePropertyName artistSourceUrl -NotePropertyValue $sourceUrl -Force
$artistCount = @($cardsDocument.cards | Where-Object { -not [string]::IsNullOrWhiteSpace($_.artist) }).Count
$cardCount = @($cardsDocument.cards).Count
$cardsDocument.meta.notes = @($cardsDocument.meta.notes | ForEach-Object {
    if ("$_" -match '^artist coverage is \d+/\d+:') {
        "$_" -replace '^artist coverage is \d+/\d+:', "artist coverage is $artistCount/${cardCount}:"
    } else {
        $_
    }
})
$cardsDocument | ConvertTo-Json -Depth 20 | Set-Content $cardsPath -Encoding utf8NoBOM

$logEntry = [pscustomobject]@{
    unitId = $unit.unitId
    lang = $unit.language
    status = 'confirmed'
    source = $sourceUrl
    evidence = $evidenceText
    at = $checkedAt
}
$existingEvidence = Get-Content $evidencePath -Encoding utf8
$alreadyLogged = @($existingEvidence | Where-Object {
    $_ -like ('*"unitId":"' + $unit.unitId + '"*') -and $_ -like ('*"source":"' + $sourceUrl + '"*')
}).Count -gt 0
if (-not $alreadyLogged) {
    $logEntry | ConvertTo-Json -Compress | Add-Content $evidencePath -Encoding utf8NoBOM
}

[pscustomobject]@{
    phase = 'issue-24-exs-printing-split'
    completedAt = $checkedAt
} | ConvertTo-Json | Set-Content $statePath -Encoding utf8NoBOM

Write-Host 'Updated EXS language evidence and illustrator: Keita Takahashi'
