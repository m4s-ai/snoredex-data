$ErrorActionPreference='Stop'
$V="C:\Users\marku\Claude\snorlax-cardmarket\verification"
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json

$WP='https://www.elitefourum.com/t/black-star-promos-languages/36573'
$WCD='https://www.elitefourum.com/t/modern-world-championships-decks-languages/55804'
$TWP='Elite Fourum (collector community), "Black Star Promos - languages" reference table'
$TWCD='Elite Fourum (collector community) + localized retail listings'

$EVWP='The community reference table of all Wizards Black Star Promos lists per-card language flags. Row "49 Snorlax" carries only the US flag. The reading is validated by rows that do list several languages, e.g. "8 Mew" and "20 Psyduck" both show us/de/fr/it/es/pt - so a lone US flag is a positive statement of English-only, not a missing value.'
$EVWCD='"Historically, the worlds championships decks have only been printed in English, but ... the recent decks have also been printed in a couple other languages. It appears to have started in 2022 ... We confirmed French and Italian decks"; a second poster documents the German 2022 release under the retail name "Pokemon Weltmeisterschaftsdeck 2022". For 2023 specifically, localized retail listings exist: keepseven.de "Pokemon 2023 Weltmeisterschaftsdeck DE" (flagged DE next to English stock) and Italian retailers (GameStop.it, Gamelife.it, pianetahobby.it) listing "Mazzo dei Campionati Mondiali 2023". Spanish and Portuguese are called "less likely" in the thread and no localized listing was found - left open.'

$c=0;$x=0;$ev=@()
foreach($u in $units){
  if($u.status -in @('confirmed','contradicted','needs-manual-review')){continue}
  if($u.setCode -eq 'WP' -and $u.language -in @('French','German','Italian','Portuguese','Spanish')){
    $u.status='contradicted'; $u.sourceUrl=$WP; $u.sourceType=$TWP; $u.evidence=$EVWP; $x++
  }
  elseif($u.setCode -eq 'WCD23 LOR' -and $u.language -in @('English','German','French','Italian')){
    $u.status='confirmed'; $u.sourceUrl=$WCD; $u.sourceType=$TWCD; $u.evidence=$EVWCD; $c++
  }
  else { continue }
  $u.checkedAt=(Get-Date -Format s)
  $ev+=[pscustomobject]@{unitId=$u.unitId;lang=$u.language;status=$u.status;source=$u.sourceUrl;evidence=$u.evidence;at=$u.checkedAt}
}
$units|ConvertTo-Json -Depth 4|Set-Content "$V\units.json" -Encoding utf8
if($ev){ $ev|ForEach-Object{$_|ConvertTo-Json -Compress}|Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='forum';completedAt=(Get-Date -Format s)}|ConvertTo-Json|Set-Content "$V\state.json" -Encoding utf8
Write-Host "confirmed: $c   contradicted: $x"
$units|Group-Object status|Sort-Object Count -Desc|Format-Table Count,Name -Auto
