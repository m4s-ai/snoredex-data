$ErrorActionPreference='Stop'
$V="C:\redacted\Claude\snorlax-cardmarket\verification"
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json
$wikiBase='https://bulbapedia.bulbagarden.net/wiki/'
$srcType='Bulbapedia (fan wiki), product article, DeckInfobox "release" field'

function NormNum($n){ if($null -eq $n){return ''}; $s="$n".Trim(); if($s -eq ''){return ''}
  if($s -match '^[A-Za-z\-]*?(\d+)$'){ return [string][int]$Matches[1] }; return $s.ToUpper() }

# Deck and collection products list their per-language release dates in the infobox
# "release" field, not in an "In other languages" table. Earlier passes only checked
# the latter, which is why these read as undocumented for so long.
$claims=@(
 [pscustomobject]@{code='sN';    num='008'; lang='Korean';    page='Start_Deck_100_CoroCoro_Comic_Version_(TCG)'
   ev='Infobox release field: "Japanese: March 2022 / Korean: May 27, 2022 / Traditional Chinese: October 2, 2022". Article text: "The deck was later released in South Korea on May 27, 2022 under the name Start Deck 100 「피카츄 V & 이브이 V」".'}
 [pscustomobject]@{code='svIba'; num='046'; lang='S-Chinese'; page='Pok%C3%A9mon_Card_Game_Battle_Academy_(TCG)'
   ev='Infobox release field: "March 8, 2024 (Japan) / April 20, 2024 (South Korea) / January 16, 2026 (Mainland China)". Mainland China is the Simplified Chinese market.'}
 [pscustomobject]@{code='sI100'; num='341'; lang='Korean';    page='Start_Deck_100_(TCG)'
   ev='Infobox release field: "Japanese: December 17, 2021 / Traditional Chinese: February 18, 2022 / Korean: April 23, 2022 / Simplified Chinese: May 17, 2024".'}
 [pscustomobject]@{code='sI100'; num='342'; lang='Korean';    page='Start_Deck_100_(TCG)'
   ev='Infobox release field: "Japanese: December 17, 2021 / Traditional Chinese: February 18, 2022 / Korean: April 23, 2022 / Simplified Chinese: May 17, 2024".'}
 [pscustomobject]@{code='sI100'; num='342'; lang='S-Chinese'; page='Start_Deck_100_(TCG)'
   ev='Infobox release field lists "Simplified Chinese: May 17, 2024" for this product.'}
 [pscustomobject]@{code='20th';  num='047'; lang='Korean';    page='Generations_(TCG)'
   ev='Article section "Languages this set is released in": "The 20th Anniversary Starter Pack is released in Japanese and Korean, both only available in unlimited edition."'}
 [pscustomobject]@{code='sH';    num='038'; lang='S-Chinese'; page='Sword_%26_Shield_Family_Pok%C3%A9mon_Card_Game_(TCG)'
   ev='Infobox release field: "Japanese: July 9, 2021 / Korean: November 27, 2021 / Traditional Chinese: August 6, 2021 / Simplified Chinese: November 17, 2023 / Thai: November 26, 2021".'}
)
$applied=0; $logRows=@()
foreach($claim in $claims){
  foreach($unit in $units){
    if($unit.setCode -ne $claim.code){ continue }
    if((NormNum $unit.number) -ne (NormNum $claim.num)){ continue }
    if($unit.language -ne $claim.lang){ continue }
    if($unit.status -in @('confirmed','contradicted')){ continue }
    $unit.status='confirmed'
    $unit.sourceUrl=$wikiBase+$claim.page
    $unit.sourceType=$srcType
    $unit.evidence=$claim.ev
    $unit.checkedAt=(Get-Date -Format s)
    $logRows += [pscustomobject]@{unitId=$unit.unitId;lang=$unit.language;status='confirmed';source=$unit.sourceUrl;evidence=$unit.evidence;at=$unit.checkedAt}
    $applied++
  }
}
$units | ConvertTo-Json -Depth 4 | Set-Content "$V\units.json" -Encoding utf8
if($logRows){ $logRows | ForEach-Object{ $_ | ConvertTo-Json -Compress } | Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='release-field';completedAt=(Get-Date -Format s)} | ConvertTo-Json | Set-Content "$V\state.json" -Encoding utf8
Write-Host "confirmed: $applied"
