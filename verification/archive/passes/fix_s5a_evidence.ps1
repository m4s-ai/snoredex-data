$ErrorActionPreference='Stop'
$V=Split-Path -Parent $PSScriptRoot
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json

# Same $EV/$ev collision as in verify_svln_promo.ps1: verify_batch9.ps1 declared $EV as the
# evidence template and then $ev=@() as the log array, wiping it. The units were written with
# an empty evidence string. Distinct variable names below.
$srcUrl  = 'https://bulbapedia.bulbagarden.net/wiki/List_of_Pok%C3%A9mon_Trading_Card_Game_expansions_in_other_languages'
$srcType = 'Bulbapedia (fan wiki), cross-language expansion index (raw wikitext via MediaWiki API)'
$textByLang = @{}
$textByLang['Indonesian'] = 'Cross-language expansion index row for 双璧のファイター / Peerless Fighters (Cardmarket calls this set "Matchless Fighters") carries a localized Indonesian set name: "Dua Pilar Petarung". Full row: 双璧のファイター | Peerless Fighters | 雙璧戰士 | Dua Pilar Petarung | สองยอดนักสู้ | 쌍벽의 파이터.'
$textByLang['Thai']       = 'Cross-language expansion index row for 双璧のファイター / Peerless Fighters (Cardmarket calls this set "Matchless Fighters") carries a localized Thai set name: "สองยอดนักสู้". Full row: 双璧のファイター | Peerless Fighters | 雙璧戰士 | Dua Pilar Petarung | สองยอดนักสู้ | 쌍벽의 파이터.'

$fixed=0
foreach($unit in $units){
  if($unit.setCode -ne 's5a'){ continue }
  if(-not $textByLang.ContainsKey($unit.language)){ continue }
  $unit.status='confirmed'
  $unit.sourceUrl=$srcUrl
  $unit.sourceType=$srcType
  $unit.evidence=$textByLang[$unit.language]
  $unit.checkedAt=(Get-Date -Format s)
  $fixed++
}
$units | ConvertTo-Json -Depth 4 | Set-Content "$V\units.json" -Encoding utf8
Write-Host "fixed: $fixed"
