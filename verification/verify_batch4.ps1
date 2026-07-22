$ErrorActionPreference='Stop'
$V="C:\redacted\Claude\snorlax-cardmarket\verification"
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json
$B='https://bulbapedia.bulbagarden.net/wiki/'
function NN($n){ if($null -eq $n){return ''}; $s="$n".Trim(); if($s -eq ''){return ''}
  if($s -match '^[A-Za-z\-]*?(\d+)$'){ return [string][int]$Matches[1] }; return $s.ToUpper() }

$rows=@(
 [pscustomobject]@{code='smL'; num='038'; langs=@('Korean'); page='Sun_%26_Moon_Family_Pok%C3%A9mon_Card_Game_(TCG)'
   type='Bulbapedia (fan wiki), product article, "In other languages" table + set list'
   ev='official Korean product name |ko=패밀리 포켓몬 카드 게임 ("Family Pokémon Card Game"); set list row 038/051 Snorlax, Colorless'}
 [pscustomobject]@{code='sH';  num='038'; langs=@('Korean'); page='Sword_%26_Shield_Family_Pok%C3%A9mon_Card_Game_(TCG)'
   type='Bulbapedia (fan wiki), product article, "In other languages" table + set list'
   ev='official Korean product name |ko=패밀리 포켓몬 카드 게임; set list row 038/053 Snorlax, Colorless'}
 [pscustomobject]@{code='sI100'; num='341'; langs=@('S-Chinese'); page='Start_Deck_100_(TCG)'
   type='Bulbapedia (fan wiki), product article'
   ev='"Gossifleur, Eldegoss, Blissey V, Snorlax 341, Rufflet, Braviary and Level Ball''s Holofoil prints are only included in Deck No. 102 and thus exclusive to Simplified Chinese." Set list row: 341/414 Snorlax, Colorless.'}
)
$n=0;$ev=@()
foreach($r in $rows){
  foreach($u in $units){
    if($u.setCode -ne $r.code){continue}
    if((NN $u.number) -ne (NN $r.num)){continue}
    if($u.language -notin $r.langs){continue}
    if($u.status -in @('confirmed','contradicted')){continue}
    $u.status='confirmed'; $u.sourceUrl=$B+$r.page; $u.sourceType=$r.type; $u.evidence=$r.ev
    $u.checkedAt=(Get-Date -Format s)
    $ev+=[pscustomobject]@{unitId=$u.unitId;lang=$u.language;status='confirmed';source=$u.sourceUrl;evidence=$u.evidence;at=$u.checkedAt}
    $n++
  }
}
$units|ConvertTo-Json -Depth 4|Set-Content "$V\units.json" -Encoding utf8
if($ev){ $ev|ForEach-Object{$_|ConvertTo-Json -Compress}|Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='batch4';completedAt=(Get-Date -Format s)}|ConvertTo-Json|Set-Content "$V\state.json" -Encoding utf8
Write-Host "confirmed: $n"
$units|Group-Object status|Sort-Object Count -Desc|Format-Table Count,Name -Auto
