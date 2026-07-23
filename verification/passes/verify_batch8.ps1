$ErrorActionPreference='Stop'
$V=Split-Path -Parent $PSScriptRoot
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json
$B='https://bulbapedia.bulbagarden.net/wiki/'
$TYPE='Bulbapedia (fan wiki), per-language promo series article'
function NN($n){ if($null -eq $n){return ''}; $s="$n".Trim(); if($s -eq ''){return ''}
  if($s -match '^[A-Za-z\-]*?(\d+)$'){ return [string][int]$Matches[1] }; return $s.ToUpper() }

$rows=@(
 [pscustomobject]@{code='S-P/CS';  num='061'; lang='S-Chinese'; page='S-P_Promotional_cards_(SCTCG)'
   ev='Simplified Chinese promo series article, set list row 061/S-P Snorlax, Pokémon TCG Event Promo Pack A Vol. 2 - exact number match with Cardmarket'}
 [pscustomobject]@{code='SV-P/CS'; num='277'; lang='S-Chinese'; page='SV-P_Promotional_cards_(SCTCG)'
   ev='Simplified Chinese promo series article, set list row 277/SV-P Snorlax (reprint of Surging Sparks 144), Scarlet & Violet Event Special Pack Part 3 - exact number match with Cardmarket'}
)
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
@{phase='batch8';completedAt=(Get-Date -Format s)}|ConvertTo-Json|Set-Content "$V\state.json" -Encoding utf8
Write-Host "confirmed: $n"
$units|Group-Object status|Sort-Object Count -Desc|Format-Table Count,Name -Auto
