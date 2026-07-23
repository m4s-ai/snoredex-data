$ErrorActionPreference='Stop'
$V=Split-Path -Parent $PSScriptRoot
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json
$B='https://bulbapedia.bulbagarden.net/wiki/'
function NN($n){ if($null -eq $n){return ''}; $s="$n".Trim(); if($s -eq ''){return ''}
  if($s -match '^[A-Za-z\-]*?(\d+)$'){ return [string][int]$Matches[1] }; return $s.ToUpper() }

$EVMC='Product article "In other languages": |ko=스타트 덱 100 배틀컬렉션 ("Start Deck 100 Battle Collection"), plus zh_yue/zh_cmn entries; fr/de/it/es/pt_br/id/th are present but EMPTY, i.e. deliberately not released there. External links include the Korean official shop pokemoncard.co.kr. Set list rows 567/742, 568/742 and 569/742 cover all three Cardmarket products.'
$rows=@(
 [pscustomobject]@{code='mC'; num='567'; lang='Korean'; page='Start_Deck_100_Battle_Collection_(TCG)'; ev=$EVMC}
 [pscustomobject]@{code='mC'; num='568'; lang='Korean'; page='Start_Deck_100_Battle_Collection_(TCG)'; ev=$EVMC}
 [pscustomobject]@{code='mC'; num='569'; lang='Korean'; page='Start_Deck_100_Battle_Collection_(TCG)'; ev=$EVMC}
 [pscustomobject]@{code='UNP'; num=''; lang='Japanese'; page='Hungry_Snorlax_(Nintendo_64_promo)'
   ev='dedicated card article for the Japanese Nintendo 64 promotional card "Hungry Snorlax" (Colorless, species Snorlax), the unnumbered promo Cardmarket files under UNP'}
)
$TYPE='Bulbapedia (fan wiki), product/card article'
$n=0;$ev=@()
foreach($r in $rows){
  foreach($u in $units){
    if($u.setCode -ne $r.code){continue}
    if((NN $u.number) -ne (NN $r.num)){continue}
    if($u.language -ne $r.lang){continue}
    if($u.status -in @('confirmed','contradicted')){continue}
    $u.status='confirmed'; $u.sourceUrl=$B+$r.page; $u.sourceType=$TYPE; $u.evidence=$r.ev
    $u.checkedAt=(Get-Date -Format s)
    $ev+=[pscustomobject]@{unitId=$u.unitId;lang=$u.language;status='confirmed';source=$u.sourceUrl;evidence=$u.evidence;at=$u.checkedAt}
    $n++
  }
}
$units|ConvertTo-Json -Depth 4|Set-Content "$V\units.json" -Encoding utf8
if($ev){ $ev|ForEach-Object{$_|ConvertTo-Json -Compress}|Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='batch7';completedAt=(Get-Date -Format s)}|ConvertTo-Json|Set-Content "$V\state.json" -Encoding utf8
Write-Host "confirmed: $n"
$units|Group-Object status|Sort-Object Count -Desc|Format-Table Count,Name -Auto
