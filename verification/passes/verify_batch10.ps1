$ErrorActionPreference='Stop'
$V="C:\Users\marku\Claude\snorlax-cardmarket\verification"
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json
$B='https://bulbapedia.bulbagarden.net/wiki/'
function NN($n){ if($null -eq $n){return ''}; $s="$n".Trim(); if($s -eq ''){return ''}
  if($s -match '^[A-Za-z\-]*?(\d+)$'){ return [string][int]$Matches[1] }; return $s.ToUpper() }

$rows=@(
 [pscustomobject]@{code='s1H'; num='70'; lang='Japanese'; page='Snorlax_VMAX_(Sword_%26_Shield_142)'
   type='Bulbapedia (fan wiki), card article, "Release information"'
   ev='"This card was included as both a Regular card and a Secret card in the Sword & Shield expansion, first released in the Japanese Shield expansion. Both prints feature artwork by aky CG Works." The Secret print is English 206 / Japanese Shield 070; the article is categorised under "Shield cards".'}
 [pscustomobject]@{code='EXS'; num=''; lang='Japanese'; page='Snorlax_(TCG)'
   type='Bulbapedia (fan wiki), master card list for the species'
   ev='release list for this card: jpset "Expansion Sheet 1" (Vending Machine cards), Uncommon; also jpset "Red Deck" (Quick Starter Gift Set); the English counterpart is Wizards Black Star Promos 49'}
)
$n=0;$ev=@()
foreach($r in $rows){
  foreach($u in $units){
    if($u.setCode -ne $r.code){continue}
    if((NN $u.number) -ne (NN $r.num)){continue}
    if($u.language -ne $r.lang){continue}
    if($u.status -in @('confirmed','contradicted')){continue}
    $u.status='confirmed'; $u.sourceUrl=$B+$r.page; $u.sourceType=$r.type; $u.evidence=$r.ev
    $u.checkedAt=(Get-Date -Format s)
    $ev+=[pscustomobject]@{unitId=$u.unitId;lang=$u.language;status='confirmed';source=$u.sourceUrl;evidence=$u.evidence;at=$u.checkedAt}
    $n++
  }
}
$units|ConvertTo-Json -Depth 4|Set-Content "$V\units.json" -Encoding utf8
if($ev){ $ev|ForEach-Object{$_|ConvertTo-Json -Compress}|Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='batch10';completedAt=(Get-Date -Format s)}|ConvertTo-Json|Set-Content "$V\state.json" -Encoding utf8
Write-Host "confirmed: $n"
$units|Group-Object status|Sort-Object Count -Desc|Format-Table Count,Name -Auto
