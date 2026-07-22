$ErrorActionPreference='Stop'
$V="C:\Users\marku\Claude\snorlax-cardmarket\verification"
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json
$WIKI='https://bulbapedia.bulbagarden.net/wiki/SV-P_Promotional_cards_(TCTCG)'
$EBAY='https://www.ebay.com/itm/306828513318'
$TYPE='Bulbapedia (fan wiki), Traditional Chinese promo series article + marketplace listing'

# The Traditional Chinese printing of this card is NOT a TC edition of the Japanese starter deck.
# It is the SV-P 215 promo. Card identity is established by the shared Cardmarket cardKey
# "Snorlax-Spike-Draw-Mega-Punch", which also covers Surging Sparks 144 - and the TCTCG article
# records 215/SV-P as a reprint of exactly that card.
$EV='Traditional Chinese printing exists as the promo SV-P 215: the TCTCG promo series article lists "215/SV-P ... {{TCG ID|Surging Sparks|Snorlax|144}} ... 2025 Taiwan Lantern Festival in Taoyuan (Taiwan, February 21-23, 2025)". This card shares the Cardmarket cardKey "Snorlax-Spike-Draw-Mega-Punch" with Surging Sparks 144, so it is the same card. Corroborated by a Taiwanese seller listing: "Snorlax 215/SV-P Promo Pokemon Chinese Taiwan Lantern Festival Sealed Exclusive". NOTE: the Traditional Chinese print is a promo under its own set and number, not a Traditional Chinese edition of the Japanese product Cardmarket files it under.'

$targets=@('svLN','mP1')
$n=0;$ev=@()
foreach($u in $units){
  if($u.setCode -notin $targets){continue}
  if($u.language -ne 'T-Chinese'){continue}
  if($u.status -in @('confirmed','contradicted')){continue}
  if($u.cardKey -ne 'Snorlax-Spike-Draw-Mega-Punch'){ Write-Host "skipped $($u.setCode) $($u.number): cardKey is '$($u.cardKey)'"; continue }
  $u.status='confirmed'; $u.sourceType=$TYPE; $u.sourceUrl=$WIKI
  $u.evidence=$EV + " Listing: $EBAY"
  $u.checkedAt=(Get-Date -Format s)
  $ev+=[pscustomobject]@{unitId=$u.unitId;lang='T-Chinese';status='confirmed';source=$WIKI;evidence=$u.evidence;at=$u.checkedAt}
  $n++
}
$units|ConvertTo-Json -Depth 4|Set-Content "$V\units.json" -Encoding utf8
if($ev){ $ev|ForEach-Object{$_|ConvertTo-Json -Compress}|Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='svln-promo';completedAt=(Get-Date -Format s)}|ConvertTo-Json|Set-Content "$V\state.json" -Encoding utf8
Write-Host "confirmed: $n"
$units|Group-Object status|Sort-Object Count -Desc|Format-Table Count,Name -Auto
