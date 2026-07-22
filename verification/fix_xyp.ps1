$ErrorActionPreference='Stop'
$V="C:\Users\marku\Claude\snorlax-cardmarket\verification"
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json

# CORRECTION. verify_xyp.ps1 contradicted Korean for XY-P 149 and 261 on the reasoning that a
# Japanese retail campaign is a Japan-only channel. That reasoning is WRONG as a general rule:
# the same card can be distributed through a DIFFERENT domestic campaign in another market.
#   Japan : XY-P 149 via the Marumiya furikake/curry promotion, July 2015
#   Korea : XY-P 167 via the Kisstick sausages promotion, 2017
# Bulbapedia redirects BOTH "Snorlax (XY-P Promo 149)" and "Snorlax (XY-P Promo 167)" to the same
# card article, "Snorlax (BREAKthrough 118)" - i.e. the wiki itself treats them as one card.
# The illustrator matches too: Kouki Saitou on the Korean listing and on BREAKthrough 118.
$wikiUrl='https://bulbapedia.bulbagarden.net/wiki/Snorlax_(BREAKthrough_118)'
$listUrl='https://pokumon.com/card/snorlax-167-xy-p-korean-promo/'

$evidence149='Korean printing exists as XY-P 167. Bulbapedia redirects both "Snorlax (XY-P Promo 149)" and "Snorlax (XY-P Promo 167)" to the same card article, "Snorlax (BREAKthrough 118)", so the wiki treats them as one card with matching artwork. Each market ran its own food-company campaign: Japan via Marumiya (furikake mini packs / curry, July 2015), Korea via the Kisstick sausages promotion (2017). Illustrator Kouki Saitou matches on both. Korean listing: ' + $listUrl

$reverted=0; $confirmed=0; $logRows=@()
foreach($unit in $units){
  if($unit.setCode -ne 'XY-P'){ continue }
  if($unit.language -ne 'Korean'){ continue }
  $num="$($unit.number)".Trim()
  if($num -eq '149'){
    $unit.status='confirmed'
    $unit.sourceUrl=$wikiUrl
    $unit.sourceType='Bulbapedia (fan wiki), card article redirect target + collector listing'
    $unit.evidence=$evidence149
    $confirmed++
  }
  elseif($num -eq '261'){
    # The contradiction here was an unjustified extension of the 149 reasoning. No evidence either way.
    $unit.status='pending'
    $unit.sourceUrl=$null; $unit.sourceType=$null
    $unit.evidence='REVERTED: previously contradicted by extending the "Japan-only retail campaign" argument from XY-P 149. That argument does not hold - XY-P 149 turned out to have a Korean printing through a separate Korean campaign. XY-P 261 corresponds to a different card (Bulbapedia redirects it to "Snorlax (XY Promo 179)"), and no Korean evidence has been found either way.'
    $reverted++
  }
  else { continue }
  $unit.checkedAt=(Get-Date -Format s)
  $logRows += [pscustomobject]@{unitId=$unit.unitId;lang='Korean';status=$unit.status;source=$unit.sourceUrl;evidence=$unit.evidence;at=$unit.checkedAt}
}
$units | ConvertTo-Json -Depth 4 | Set-Content "$V\units.json" -Encoding utf8
if($logRows){ $logRows | ForEach-Object{ $_ | ConvertTo-Json -Compress } | Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='xyp-correction';completedAt=(Get-Date -Format s)} | ConvertTo-Json | Set-Content "$V\state.json" -Encoding utf8
Write-Host "149 corrected to confirmed: $confirmed ; 261 reverted to pending: $reverted"
