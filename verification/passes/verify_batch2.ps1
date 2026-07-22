$ErrorActionPreference='Stop'
$V="C:\Users\marku\Claude\snorlax-cardmarket\verification"
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json
$B='https://bulbapedia.bulbagarden.net/wiki/'

function NN($n){ if($null -eq $n){return ''}; $s="$n".Trim()
  if($s -match '^[A-Za-z\-]*?(\d+)$'){ return [string][int]$Matches[1] }; return $s.ToUpper() }

$rows=@(
 [pscustomobject]@{code='SK';  num='100'; langs=@('Italian'); page='Skyridge_(TCG)'; type='Bulbapedia (fan wiki), expansion article, "Languages this set is released in"'
   ev='"The Skyridge set is released in English, German, and Italian, with all cards except the H/32 cards also available as Reverse Holos."'}
 [pscustomobject]@{code='EC5'; num='062'; langs=@('Japanese'); page='Skyridge_(TCG)'; type='Bulbapedia (fan wiki), expansion article, "Languages this set is released in"'
   ev='"The Split Earth and Mysterious Mountains sets are only released in Japanese, in both 1st and unlimited edition." Set list row: 062/088 Snorlax, Colorless, Common.'}
 [pscustomobject]@{code='HIF'; num='50'; langs=@('Portuguese'); page='Hidden_Fates_(TCG)'; type='Bulbapedia (fan wiki), expansion article, "In other languages" table'
   ev='Hidden Fates localized names include pt_br "Destinos Ocultos", alongside fr/de/it/es/ko - evidencing a Portuguese release'}
 [pscustomobject]@{code='CLV'; num='016'; langs=@('English'); page='Pok%C3%A9mon_Trading_Card_Game_Classic_(TCG)'; type='Bulbapedia (fan wiki), product article, deck list'
   ev='deck list row: 016/034 Venusaur Deck Snorlax, Colorless (English Trading Card Game Classic)'}
 [pscustomobject]@{code='CLF'; num='016'; langs=@('Japanese'); page='Pok%C3%A9mon_Trading_Card_Game_Classic_(TCG)'; type='Bulbapedia (fan wiki), product article, deck list'
   ev='deck list row: 016/032 Venusaur Deck Snorlax, Colorless (the 32-card Japanese deck configuration)'}
 [pscustomobject]@{code='CLF'; num='016'; langs=@('Korean','T-Chinese'); page='Pok%C3%A9mon_Trading_Card_Game_Classic_(TCG)'; type='Bulbapedia (fan wiki), product article, "In other languages" table'
   ev='Trading Card Game Classic localized product names include ko "포켓몬 카드 게임 Classic" and zh "寶可夢集換式卡牌遊戲 Classic", evidencing Korean and Chinese releases'}
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
@{phase='batch2';completedAt=(Get-Date -Format s)}|ConvertTo-Json|Set-Content "$V\state.json" -Encoding utf8
Write-Host "confirmed: $n"
$units|Group-Object status|Sort-Object Count -Desc|Format-Table Count,Name -Auto
