$ErrorActionPreference='Stop'
$V="C:\redacted\Claude\snorlax-cardmarket\verification"
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json
$KSS='https://bulbapedia.bulbagarden.net/wiki/Kalos_Starter_Set_(TCG)'
$TYPE='Bulbapedia (fan wiki), expansion article'

# The article states the print languages exhaustively:
# "The Kalos Starter Set is released in English, German, French, Italian, Spanish, Portuguese and Russian."
$PRINTED=@('English','German','French','Italian','Spanish','Portuguese','Russian')
$QUOTE='Kalos Starter Set print languages, stated exhaustively: English, German, French, Italian, Spanish, Portuguese and Russian'

$c=0;$x=0;$ev=@()
foreach($u in $units){
  if($u.setCode -ne 'KSS'){continue}
  if($u.status -in @('confirmed','contradicted')){continue}
  if($u.language -in $PRINTED){
    $u.status='confirmed'; $u.evidence=$QUOTE; $c++
  } else {
    $u.status='contradicted'
    $u.evidence="$QUOTE - $($u.language) is NOT among them, so Cardmarket's language filter overstates availability for this product"
    $x++
  }
  $u.sourceType=$TYPE; $u.sourceUrl=$KSS; $u.checkedAt=(Get-Date -Format s)
  $ev+=[pscustomobject]@{unitId=$u.unitId;lang=$u.language;status=$u.status;source=$KSS;evidence=$u.evidence;at=$u.checkedAt}
}
$units|ConvertTo-Json -Depth 4|Set-Content "$V\units.json" -Encoding utf8
if($ev){ $ev|ForEach-Object{$_|ConvertTo-Json -Compress}|Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='kss-closure';completedAt=(Get-Date -Format s)}|ConvertTo-Json|Set-Content "$V\state.json" -Encoding utf8
Write-Host "KSS 26 closed - confirmed: $c   contradicted: $x"
$units|Group-Object status|Sort-Object Count -Desc|Format-Table Count,Name -Auto
