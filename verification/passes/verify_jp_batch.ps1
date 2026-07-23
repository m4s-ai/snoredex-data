$ErrorActionPreference='Stop'
$V=Split-Path -Parent $PSScriptRoot
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json
$B='https://bulbapedia.bulbagarden.net/wiki/'
$TSET='Bulbapedia (fan wiki), expansion set list (Japanese numbering)'
$TJP='Official Pokemon Japan card database (pokemon-card.com)'

function NN($n){ if($null -eq $n){return ''}; $s="$n".Trim()
  if($s -eq ''){return ''}
  if($s -match '^[A-Za-z\-]*?(\d+)$'){ return [string][int]$Matches[1] }; return $s.ToUpper() }

$rows=@(
 [pscustomobject]@{code='sm9'; num='115'; page='Team_Up_(TCG)';           type=$TSET
   ev='Japanese Tag Bolt set list row: 115/095 Eevee & Snorlax-GX, Colorless, HR (Hyper/Rainbow Rare). Cardmarket "Tag Bolt" = Bulbapedia article "Team Up (TCG)", which carries both numberings.'}
 [pscustomobject]@{code='s5a'; num='93';  page='Peerless_Fighters_(TCG)'; type=$TSET
   ev='Japanese set list row: 093/070 Snorlax, Colorless, UR. Cardmarket "Matchless Fighters" = Bulbapedia "Peerless Fighters".'}
 [pscustomobject]@{code='PJU'; num='';    page='Jungle_(TCG)';            type=$TSET
   ev='set list row for the Japanese Pokémon Jungle expansion: Snorlax, Colorless, Rare Holo (no collector number in that print run)'}
 [pscustomobject]@{code='G2';  num='';    page='Gym_Challenge_(TCG)';     type=$TSET
   ev='set list row for the Japanese Challenge from the Darkness expansion: Rocket''s Snorlax, Colorless, Rare (no collector number)'}
)
$n=0;$ev=@()
foreach($r in $rows){
  foreach($u in $units){
    if($u.setCode -ne $r.code){continue}
    if((NN $u.number) -ne (NN $r.num)){continue}
    if($u.language -ne 'Japanese'){continue}
    if($u.status -in @('confirmed','contradicted')){continue}
    $u.status='confirmed'; $u.sourceUrl=$B+$r.page; $u.sourceType=$r.type; $u.evidence=$r.ev
    $u.checkedAt=(Get-Date -Format s)
    $ev+=[pscustomobject]@{unitId=$u.unitId;lang='Japanese';status='confirmed';source=$u.sourceUrl;evidence=$u.evidence;at=$u.checkedAt}
    $n++
  }
}

# SM-P promos: the official JP promo pages carry no collector number, and an earlier
# matcher rejected them because "カビゴンGX" is a substring of "イーブイ&カビゴンGX".
# Exact-name matching disambiguates them.
$J="$V\cache\jp"
$promo=@{}
foreach($f in (Get-ChildItem $J -Filter 'card_*.json')){
  $rec=Get-Content $f.FullName -Raw -Encoding utf8|ConvertFrom-Json
  if($rec.number){continue}
  if(($rec.setCode -replace '[^A-Za-z0-9]','').ToUpper() -ne 'SMP'){continue}
  $nm=($rec.name -replace '&amp;','&')
  $promo[$nm]=$rec
}
$map=@{ 'Snorlax GX'='カビゴンGX'; 'Eevee & Snorlax GX'='イーブイ&カビゴンGX' }
foreach($u in $units){
  if($u.setCode -ne 'SM-P'){continue}
  if($u.language -ne 'Japanese'){continue}
  if($u.status -in @('confirmed','contradicted')){continue}
  $want=$map[$u.cardName]; if(-not $want){continue}
  $rec=$promo[$want]; if(-not $rec){continue}
  $u.status='confirmed'; $u.sourceType=$TJP; $u.sourceUrl=$rec.url
  $u.evidence="official JP promo entry: set=$($rec.setCode) name=$($rec.name) illustrator=$($rec.illustrator) (promo page carries no collector number; matched on exact card name)"
  $u.checkedAt=(Get-Date -Format s)
  if(-not $u.artist -and $rec.illustrator){ $u.artist=$rec.illustrator }
  $ev+=[pscustomobject]@{unitId=$u.unitId;lang='Japanese';status='confirmed';source=$rec.url;evidence=$u.evidence;at=$u.checkedAt}
  $n++
}
$units|ConvertTo-Json -Depth 4|Set-Content "$V\units.json" -Encoding utf8
if($ev){ $ev|ForEach-Object{$_|ConvertTo-Json -Compress}|Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='jp-batch';completedAt=(Get-Date -Format s)}|ConvertTo-Json|Set-Content "$V\state.json" -Encoding utf8
Write-Host "Japanese units confirmed: $n"
$units|Group-Object status|Sort-Object Count -Desc|Format-Table Count,Name -Auto
