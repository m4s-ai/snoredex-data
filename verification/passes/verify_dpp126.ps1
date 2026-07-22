$ErrorActionPreference='Stop'
$V="C:\Users\marku\Claude\snorlax-cardmarket\verification"
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json

$srcUrl  = 'https://bulbapedia.bulbagarden.net/wiki/DP-P_Promotional_cards_(TCG)'
$srcType = 'Bulbapedia (fan wiki), Japanese promo series article + Korean promo series article'
$evidenceText = 'Japan-only distribution. The Japanese DP-P series lists "126/DP-P Snorlax ... Domino''s Pizza Exciting Pokemon Pack (October-December 2008)" - a Japanese fast-food campaign with no Korean equivalent. The Korean series "Black Star Promos (KTCG)" does contain the sibling card "006 Snorlax LV.X ... Promo pack 2" (the Japanese DP-P 127, distributed in Korea through a Korean promo pack instead), which shows the Korean list does cover Snorlax cards of this era - so the absence of the Lv.37 is meaningful rather than a gap in coverage. CAVEAT: the Korean article is {{incomplete}}-tagged and lists only 22 cards. User (domain expert) confirms the card did not appear in Korea.'

$changed=0; $log=@()
foreach($unit in $units){
  if($unit.setCode -ne 'DP-P'){ continue }
  if($unit.language -ne 'Korean'){ continue }
  if($unit.cardName -notlike '*Lv.37*'){ continue }
  if($unit.status -in @('confirmed','contradicted')){ continue }
  $unit.status='contradicted'
  $unit.sourceUrl=$srcUrl; $unit.sourceType=$srcType; $unit.evidence=$evidenceText
  $unit.checkedAt=(Get-Date -Format s)
  $log += [pscustomobject]@{unitId=$unit.unitId;lang=$unit.language;status='contradicted';source=$srcUrl;evidence=$evidenceText;at=$unit.checkedAt}
  $changed++
}
$units | ConvertTo-Json -Depth 4 | Set-Content "$V\units.json" -Encoding utf8
if($log){ $log | ForEach-Object{ $_ | ConvertTo-Json -Compress } | Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='dpp126';completedAt=(Get-Date -Format s)} | ConvertTo-Json | Set-Content "$V\state.json" -Encoding utf8
Write-Host "contradicted: $changed"
