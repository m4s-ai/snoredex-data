$ErrorActionPreference='Stop'
$V=Split-Path -Parent $PSScriptRoot
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json
$SRC='https://bulbapedia.bulbagarden.net/wiki/List_of_Pok%C3%A9mon_Trading_Card_Game_expansions_in_other_languages'
$TYPE='Bulbapedia (fan wiki), cross-language expansion index (raw wikitext via MediaWiki API)'

# Found only after searching the index under Bulbapedia's name for the set, not Cardmarket's.
# Cardmarket "Matchless Fighters" is listed there as "Peerless Fighters":
#   双璧のファイター | Peerless Fighters | 雙璧戰士 | Dua Pilar Petarung | สองยอดนักสู้ | 쌍벽의 파이터
$EV='cross-language expansion index row for 双璧のファイター / Peerless Fighters (Cardmarket calls it "Matchless Fighters") carries a localized {0} set name: {1}'
$rows=@(
 [pscustomobject]@{code='s5a'; lang='Indonesian'; name='Dua Pilar Petarung'}
 [pscustomobject]@{code='s5a'; lang='Thai';       name='สองยอดนักสู้'}
)
$n=0;$ev=@()
foreach($r in $rows){
  foreach($u in $units){
    if($u.setCode -ne $r.code){continue}
    if($u.language -ne $r.lang){continue}
    if($u.status -in @('confirmed','contradicted')){continue}
    $u.status='confirmed'; $u.sourceUrl=$SRC; $u.sourceType=$TYPE
    $u.evidence=($EV -f $r.lang,$r.name)
    $u.checkedAt=(Get-Date -Format s)
    $ev+=[pscustomobject]@{unitId=$u.unitId;lang=$u.language;status='confirmed';source=$SRC;evidence=$u.evidence;at=$u.checkedAt}
    $n++
  }
}
$units|ConvertTo-Json -Depth 4|Set-Content "$V\units.json" -Encoding utf8
if($ev){ $ev|ForEach-Object{$_|ConvertTo-Json -Compress}|Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='batch9';completedAt=(Get-Date -Format s)}|ConvertTo-Json|Set-Content "$V\state.json" -Encoding utf8
Write-Host "confirmed: $n"
$units|Group-Object status|Sort-Object Count -Desc|Format-Table Count,Name -Auto
