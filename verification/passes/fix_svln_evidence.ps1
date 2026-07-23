$ErrorActionPreference='Stop'
$V=Split-Path -Parent $PSScriptRoot
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json

# FIX. The previous run used $EV for the evidence text and $ev for the log array.
# PowerShell variable names are case-insensitive, so $ev=@() wiped the text and the
# units were written with an empty/array evidence field. Same class of bug as $R/$r earlier.
# Distinct names only from here on.
$wikiUrl  = 'https://bulbapedia.bulbagarden.net/wiki/SV-P_Promotional_cards_(TCTCG)'
$ebayUrl  = 'https://www.ebay.com/itm/306828513318'
$srcType  = 'Bulbapedia (fan wiki), Traditional Chinese promo series article + marketplace listing'
$evidenceText = 'Traditional Chinese printing exists as the promo SV-P 215. The TCTCG promo series article lists row "215/SV-P ... Surging Sparks Snorlax 144 ... 2025 Taiwan Lantern Festival in Taoyuan (Taiwan, February 21-23, 2025)". This card shares the Cardmarket cardKey "Snorlax-Spike-Draw-Mega-Punch" with Surging Sparks 144, establishing it is the same card. Corroborated by a Taiwan-based seller listing titled "Snorlax 215/SV-P Promo Pokemon Chinese Taiwan Lantern Festival Sealed Exclusive" (' + $ebayUrl + '). NOTE: the Traditional Chinese print is a promo with its own set and number, not a Traditional Chinese edition of the Japanese product Cardmarket files it under.'

$fixed=0
foreach($unit in $units){
  if($unit.unitId -notin @('U0674','U0678')){ continue }
  $unit.status='confirmed'
  $unit.sourceUrl=$wikiUrl
  $unit.sourceType=$srcType
  $unit.evidence=$evidenceText
  $unit.checkedAt=(Get-Date -Format s)
  $fixed++
}
$units | ConvertTo-Json -Depth 4 | Set-Content "$V\units.json" -Encoding utf8

# verify round-trip
$check=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json
foreach($id in @('U0674','U0678')){
  $x=@($check|Where-Object{$_.unitId -eq $id})[0]
  Write-Host ("{0} {1,-6} {2,-4} status={3} evidenceType={4} evLen={5}" -f `
    $id,$x.setCode,$x.number,$x.status,$x.evidence.GetType().Name,$x.evidence.Length)
}
Write-Host "fixed: $fixed"
