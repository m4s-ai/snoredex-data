$ErrorActionPreference='Stop'
$V="C:\redacted\Claude\snorlax-cardmarket\verification"
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json
$B='https://bulbapedia.bulbagarden.net/wiki/'
function NN($n){ if($null -eq $n){return ''}; $s="$n".Trim(); if($s -eq ''){return ''}
  if($s -match '^[A-Za-z\-]*?(\d+)$'){ return [string][int]$Matches[1] }; return $s.ToUpper() }

# Bulbapedia keeps one promo-series article per language:
#   (TCG)=Japanese  (KTCG)=Korean  (TCTCG)=Traditional Chinese  (ITCG)=Indonesian  (ATCG)=Simplified Chinese
$rows=@(
 [pscustomobject]@{code='SV-P/ID'; num='117'; lang='Indonesian'; page='SV-P_Promotional_cards_(ITCG)'
   ev='Indonesian promo series article ("a series of Indonesian promotional cards"), set list row 117/SV-P Snorlax, 2024 Monthly Promo Card (June 28 - July 25, 2024)'}
 [pscustomobject]@{code='SV-P/ID'; num='278'; lang='Indonesian'; page='SV-P_Promotional_cards_(ITCG)'
   ev='Indonesian promo series article, set list row 278/SV-P Snorlax, Pokémon Card Gym Promo Card Pack 11 (July 25, 2025)'}
 [pscustomobject]@{code='SV-P/ID'; num='286'; lang='Indonesian'; page='SV-P_Promotional_cards_(ITCG)'
   ev='Indonesian promo series article, set list row 286/SV-P Snorlax, Taro Pokémon promotion (January - February 2026)'}
 [pscustomobject]@{code='PKMTCH S-P'; num='S-P 145'; lang='T-Chinese'; page='S-P_Promotional_cards_(TCTCG)'
   ev='Traditional Chinese promo series article, set list row 145/S-P Snorlax, Sword & Shield Poké Ball Gift Box - exact number match with Cardmarket'}
 [pscustomobject]@{code='SM-P'; num='1'; lang='Korean'; page='SM-P_Promotional_cards_(KTCG)'
   ev='Korean promo series article, set list row 017/SM-P Snorlax-GX (Snorlax-GX Card Box Set). NOTE: the Korean promo series numbers independently, so the Korean printing of this card is 017/SM-P while Cardmarket files it under the Japanese number SM-P 1.'}
 [pscustomobject]@{code='SM-P'; num='297'; lang='Korean'; page='SM-P_Promotional_cards_(KTCG)'
   ev='Korean promo series article, set list row 140/SM-P Eevee & Snorlax-GX (Tag Bolt & Night Unison booster box purchase campaign). NOTE: Korean promo numbering is independent; Cardmarket files it under the Japanese number SM-P 297.'}
)
$TYPE='Bulbapedia (fan wiki), per-language promo series article'
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
@{phase='promo-families';completedAt=(Get-Date -Format s)}|ConvertTo-Json|Set-Content "$V\state.json" -Encoding utf8
Write-Host "confirmed: $n"
$units|Group-Object status|Sort-Object Count -Desc|Format-Table Count,Name -Auto
