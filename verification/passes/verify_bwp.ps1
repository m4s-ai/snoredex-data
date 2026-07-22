$ErrorActionPreference='Stop'
$V="C:\redacted\Claude\snorlax-cardmarket\verification"
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json

$srcUrl  = 'https://bulbapedia.bulbagarden.net/wiki/BW-P_Promotional_cards_(TCG)'
$srcType = 'Bulbapedia (fan wiki), Japanese promo series article + Korean promo series article'
$evidenceText = 'Japan-only distribution. The Japanese BW-P series article (236 listed cards) records this card as "207/BW-P Snorlax ... CoroCoro Ichiban! March 2013 insert" - a Japanese magazine insert, a channel with no overseas equivalent. The Korean counterpart series "BW Black Star Promos (KTCG)" lists 65 cards and contains no Snorlax at all. CAVEAT: that Korean article carries an {{incomplete}} tag, though the note concerns how cards were distributed rather than which cards are listed.'

$changed=0; $log=@()
foreach($unit in $units){
  if($unit.setCode -ne 'BW-P'){ continue }
  if($unit.language -ne 'Korean'){ continue }
  if($unit.status -in @('confirmed','contradicted')){ continue }
  $unit.status='contradicted'
  $unit.sourceUrl=$srcUrl; $unit.sourceType=$srcType; $unit.evidence=$evidenceText
  $unit.checkedAt=(Get-Date -Format s)
  $log += [pscustomobject]@{unitId=$unit.unitId;lang=$unit.language;status='contradicted';source=$srcUrl;evidence=$evidenceText;at=$unit.checkedAt}
  $changed++
}
$units | ConvertTo-Json -Depth 4 | Set-Content "$V\units.json" -Encoding utf8
if($log){ $log | ForEach-Object{ $_ | ConvertTo-Json -Compress } | Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='bwp';completedAt=(Get-Date -Format s)} | ConvertTo-Json | Set-Content "$V\state.json" -Encoding utf8
Write-Host "contradicted: $changed"
