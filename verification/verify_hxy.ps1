$ErrorActionPreference='Stop'
$V="C:\Users\marku\Claude\snorlax-cardmarket\verification"
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json

# Distinct variable names throughout - see the $EV/$ev note in RESUME.md
$srcUrl  = 'https://bulbapedia.bulbagarden.net/wiki/Kalos_Starter_Set_(TCG)'
$srcType = 'Bulbapedia (fan wiki), expansion article, "Languages this set is released in"'
$evidenceText = 'The article covers two separate products. Quote: "The Beginning Set is released in Japanese and Korean, both only available in unlimited edition. The Kalos Starter Set is released in English, German, French, Italian, Spanish, Portuguese and Russian." Cardmarket''s HXY is the Japanese Beginning Set; set list row 026/039 Beginning Set Snorlax 26. The statement is exhaustive, which also corroborates the separate contradiction of T-Chinese for this product.'

$fixed=0; $log=@()
foreach($unit in $units){
  if($unit.setCode -ne 'HXY'){ continue }
  if($unit.language -ne 'Korean'){ continue }
  if($unit.status -in @('confirmed','contradicted')){ continue }
  $unit.status='confirmed'
  $unit.sourceUrl=$srcUrl; $unit.sourceType=$srcType; $unit.evidence=$evidenceText
  $unit.checkedAt=(Get-Date -Format s)
  $log += [pscustomobject]@{unitId=$unit.unitId;lang=$unit.language;status='confirmed';source=$srcUrl;evidence=$evidenceText;at=$unit.checkedAt}
  $fixed++
}
$units | ConvertTo-Json -Depth 4 | Set-Content "$V\units.json" -Encoding utf8
if($log){ $log | ForEach-Object{ $_ | ConvertTo-Json -Compress } | Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='hxy';completedAt=(Get-Date -Format s)} | ConvertTo-Json | Set-Content "$V\state.json" -Encoding utf8
Write-Host "confirmed: $fixed"
