$ErrorActionPreference='Stop'
$V="C:\redacted\Claude\snorlax-cardmarket\verification"
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json

$listingUrl='https://www.ebay.de/itm/167623600843'
$evidenceText = 'Sealed Korean product listing. eBay item 167623600843, title "Pikachu ex & Snorlax ex Pokemon Start Deck Generations 60 Cards Korean ver", offered new / factory sealed by the commercial Korean seller RAON_KR (2518 feedback, 99.8% positive), 9 units available. The deck name matches the Japanese product exactly - Bulbapedia lists it as "Generations Start Deck Pikachu ex & Snorlax ex" (Japanese: スタートデッキGenerations ピカチュウex・カビゴンex), whose set list row 094/175 is this Snorlax ex. A sealed Korean printing of that deck therefore contains a Korean printing of this card. NOTE: this is marketplace evidence, not a card database - no database carries Korean deck contents for this product.'

$changed=0; $logRows=@()
foreach($unit in $units){
  if($unit.setCode -ne 'svM'){ continue }
  if($unit.language -ne 'Korean'){ continue }
  if($unit.status -in @('confirmed','contradicted')){ continue }
  $unit.status='confirmed'
  $unit.sourceUrl=$listingUrl
  $unit.sourceType='Marketplace listing, sealed Korean product from a Korean commercial seller'
  $unit.evidence=$evidenceText
  $unit.checkedAt=(Get-Date -Format s)
  $logRows += [pscustomobject]@{unitId=$unit.unitId;lang='Korean';status='confirmed';source=$listingUrl;evidence=$evidenceText;at=$unit.checkedAt}
  $changed++
}
$units | ConvertTo-Json -Depth 4 | Set-Content "$V\units.json" -Encoding utf8
if($logRows){ $logRows | ForEach-Object{ $_ | ConvertTo-Json -Compress } | Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='svm';completedAt=(Get-Date -Format s)} | ConvertTo-Json | Set-Content "$V\state.json" -Encoding utf8
Write-Host "confirmed: $changed"
