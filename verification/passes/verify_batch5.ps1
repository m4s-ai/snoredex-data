$ErrorActionPreference='Stop'
$V=Split-Path -Parent $PSScriptRoot
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json
$B='https://bulbapedia.bulbagarden.net/wiki/'
$TYPE='Bulbapedia (fan wiki), product article, "In other languages" table + set list'
function NN($n){ if($null -eq $n){return ''}; $s="$n".Trim(); if($s -eq ''){return ''}
  if($s -match '^[A-Za-z\-]*?(\d+)$'){ return [string][int]$Matches[1] }; return $s.ToUpper() }

$rows=@(
 [pscustomobject]@{code='s4';    num='84';  langs=@('Korean'); page='Vivid_Voltage_(TCG)'
   ev='official Korean set name |ko=앙천의 볼트태클; Japanese set list row 084/100 Snorlax, Colorless, R. Cardmarket "Shocking Volt Tackle" = Bulbapedia "Amazing Volt Tackle".'}
 [pscustomobject]@{code='svIba'; num='046'; langs=@('Korean','Japanese'); page='Pok%C3%A9mon_Card_Game_Battle_Academy_(TCG)'
   ev='official Korean product name |ko=배틀 아카데미; set list row 046/066 Snorlax, Colorless'}
 [pscustomobject]@{code='svG';   num='021'; langs=@('Korean'); page='Venusaur_%26_Charizard_%26_Blastoise_Special_Deck_Set_ex_(TCG)'
   ev='official Korean product name |ko=스페셜 덱 세트 ex 「이상해꽃·리자몽·거북왕」; set list row 021/049 Snorlax, Colorless'}
 [pscustomobject]@{code='svLN';  num='010'; langs=@('Korean'); page='Stellar_Tera_Type_Starter_Sets_(TCG)'
   ev='official Korean product name |ko=스타터 세트 테라스탈타입:스텔라 「님피아 ex」; deck list row 010/022 Snorlax, Colorless'}
 [pscustomobject]@{code='s10b';  num='056'; langs=@('Korean'); page='Pok%C3%A9mon_GO_(TCG)'
   ev='official Korean set name |ko=Pokémon GO; Japanese set list row 056/071 Snorlax, Colorless, R'}
 [pscustomobject]@{code='svM';   num='094'; langs=@('Japanese'); page='Generations_Start_Decks_(TCG)'
   ev='set list row 094/175 Snorlax ex, Colorless, from Start Deck Generations Pikachu ex / Kabigon ex'}
)
$n=0;$ev=@()
foreach($r in $rows){
  foreach($u in $units){
    if($u.setCode -ne $r.code){continue}
    if((NN $u.number) -ne (NN $r.num)){continue}
    if($u.language -notin $r.langs){continue}
    if($u.status -in @('confirmed','contradicted')){continue}
    $u.status='confirmed'; $u.sourceUrl=$B+$r.page; $u.sourceType=$TYPE; $u.evidence=$r.ev
    $u.checkedAt=(Get-Date -Format s)
    $ev+=[pscustomobject]@{unitId=$u.unitId;lang=$u.language;status='confirmed';source=$u.sourceUrl;evidence=$u.evidence;at=$u.checkedAt}
    $n++
  }
}
$units|ConvertTo-Json -Depth 4|Set-Content "$V\units.json" -Encoding utf8
if($ev){ $ev|ForEach-Object{$_|ConvertTo-Json -Compress}|Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='batch5';completedAt=(Get-Date -Format s)}|ConvertTo-Json|Set-Content "$V\state.json" -Encoding utf8
Write-Host "confirmed: $n"
$units|Group-Object status|Sort-Object Count -Desc|Format-Table Count,Name -Auto
