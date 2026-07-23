$ErrorActionPreference='Stop'
$V=Split-Path -Parent $PSScriptRoot
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json

# Hand-verified findings from named external sources.
# NOTE: use [pscustomobject], NOT nested @() arrays - PowerShell flattens those.
# Wikitext rows were read via the MediaWiki API in-browser
# (/w/api.php?action=parse&page=<T>&prop=wikitext), which avoids the truncation
# that plain page fetches hit on these long set lists.
$B='https://bulbapedia.bulbagarden.net/wiki/'
$rows=@(
 [pscustomobject]@{code='CS1aC'; num='110'; page='Dynamax_Clash_(ATCG)';                                        ev='set list row: Snorlax|110, Colorless, Uncommon (Thunder subset)'}
 [pscustomobject]@{code='CS1aC'; num='111'; page='Dynamax_Clash_(ATCG)';                                        ev='set list row: Snorlax V (Dynamax Clash Thunder 111), Double Rare'}
 [pscustomobject]@{code='CS1aC'; num='112'; page='Dynamax_Clash_(ATCG)';                                        ev='set list row: Snorlax VMAX (Dynamax Clash Thunder 112), Triple Rare'}
 [pscustomobject]@{code='CS1aC'; num='188'; page='Dynamax_Clash_(ATCG)';                                        ev='set list row: Snorlax V (Dynamax Clash Thunder 188), Secret Rare'}
 [pscustomobject]@{code='CS1aC'; num='207'; page='Dynamax_Clash_(ATCG)';                                        ev='set list row: Snorlax VMAX (Dynamax Clash Thunder 207), Hyper Rare'}
 [pscustomobject]@{code='CSM2bC';num='124'; page='Shining_Synergy_(ATCG)';                                      ev='set list row: Snorlax|124, Colorless, Rare (Supreme subset)'}
 [pscustomobject]@{code='CSM2cC';num='103'; page='Shining_Synergy_(ATCG)';                                      ev='set list row: Eevee & Snorlax-GX (Shining Synergy Summon 103), Double Rare'}
 [pscustomobject]@{code='CSM2cC';num='170'; page='Shining_Synergy_(ATCG)';                                      ev='set list row: Eevee & Snorlax-GX (Shining Synergy Summon 170), Secret Rare'}
 [pscustomobject]@{code='CSM2cC';num='171'; page='Shining_Synergy_(ATCG)';                                      ev='set list row: Eevee & Snorlax-GX (Shining Synergy Summon 171), Secret Rare'}
 [pscustomobject]@{code='CS2aC'; num='086'; page='Vivid_Portrayals_(ATCG)';                                     ev='set list row: Snorlax|86, Colorless, Rare'}
 [pscustomobject]@{code='CS2aC'; num='142'; page='Vivid_Portrayals_(ATCG)';                                     ev='set list row: Snorlax|142, Colorless, Ultra Rare'}
 [pscustomobject]@{code='151C';  num='143'; page='Collection_151_(ATCG)';                                       ev='set list row: Snorlax|143, Colorless, Uncommon'}
 [pscustomobject]@{code='151C';  num='169'; page='Collection_151_(ATCG)';                                       ev='set list row: Snorlax|169, Colorless, Shiny'}
 [pscustomobject]@{code='CSV7C'; num='158'; page='Blade_Awakening_(ATCG)';                                      ev='set list row: Snorlax|158, Colorless, Uncommon'}
 [pscustomobject]@{code='CSM1cC';num='102'; page='Storming_Emergence_(ATCG)';                                   ev='set list row: Snorlax-GX (Storming Emergence Abundant 102), Double Rare'}
 [pscustomobject]@{code='CSV10C';num='175'; page='Together_in_Pursuit_of_Glory_(ATCG)';                         ev='set list row: Snorlax|175, Colorless, Rare'}
 [pscustomobject]@{code='CSZC';  num='018'; page='Peripheral_Collection_Gift_Box:_Variety_Treasure_Box_(ATCG)'; ev='set list row: Snorlax|18, Colorless'}
 [pscustomobject]@{code='CSAC';  num='009'; page='Dynamax_Clash_Deck_Building_Gift_Box_(ATCG)';                 ev='set list row: Snorlax V (Dynamax Clash Deck Building Box 9)'}
 [pscustomobject]@{code='CSM2.1C';num='054';page='Golden_Energy_(ATCG)';                                        ev='set list row: Eevee & Snorlax-GX (Golden Energy 54)'}
 [pscustomobject]@{code='CSVH4C';num='p006';page='Decidueye_%26_Melmetal_%26_Koraidon_%26_Miraidon_Happy_Set_(ATCG)'; ev='set list row: Snorlax ex|6, Colorless'}
 [pscustomobject]@{code='CSVH4C';num='a003';page='Decidueye_%26_Melmetal_%26_Koraidon_%26_Miraidon_Happy_Set_(ATCG)'; ev='set list row: Snorlax|3, Colorless'}
 [pscustomobject]@{code='CS6bC'; num='113'; page='Marine_Shadow_(ATCG)';                                        ev='set list row: Snorlax|113, Colorless, Rare'}
 [pscustomobject]@{code='CS5aC'; num='093'; page='Gallant_Galaxy_(ATCG)';                                       ev='set list row: Snorlax|93, Colorless, Rare'}
 [pscustomobject]@{code='CSVL1C';num='109'; page='Journey_Theme_Pack_(ATCG)';                                   ev='set list row: Snorlax|109, Colorless'}
 [pscustomobject]@{code='CSMPC'; num='h009';page='Battle_Party_Set_(ATCG)';                                     ev='set list row: Snorlax|9, Colorless'}
 [pscustomobject]@{code='CS5DC'; num='097'; page='Gallant_Galaxy_V_Starter_Deck_(ATCG)';                        ev='deck list row: Snorlax|97, Colorless (Cardmarket "Brave Stars" = Bulbapedia "Gallant Galaxy")'}
 [pscustomobject]@{code='CS5DC'; num='098'; page='Gallant_Galaxy_V_Starter_Deck_(ATCG)';                        ev='deck list row: Snorlax|98, Colorless'}
 [pscustomobject]@{code='CSM2DC';num='213'; page='Shining_Synergy_GX_Starter_Deck_(ATCG)';                      ev='deck list row: Snorlax|213, Colorless'}
 [pscustomobject]@{code='CS3DC'; num='117'; page='Primordial_Arts_V_Starter_Deck_(ATCG)';                       ev='deck list row: Snorlax|117, Colorless'}
 [pscustomobject]@{code='CSVH1C';num='a001';page='Pikachu_%26_Clefairy_%26_Turtwig_%26_Gimmighoul_Happy_Set_(ATCG)'; ev='set list row: Snorlax|1, Colorless'}
 [pscustomobject]@{code='CSUC';  num='010'; page='Pok%C3%A9mon_Card_Display_Set_Gift_Box_Vol._3_(ATCG)';        ev='set list row: Snorlax|10, Colorless (Cardmarket "Display Set Gift Box Gengar")'}
 [pscustomobject]@{code='CS1DC'; num='152'; page='Dynamax_Clash_V_Starter_Deck_(ATCG)';                         ev='deck list row: Snorlax|152, Colorless'}
 [pscustomobject]@{code='CSV5C'; num='115'; page='Ardent_Obsidian_(ATCG)';                                      ev='set list row: Snorlax Doll|115, Item, Uncommon (Cardmarket "Dark Crystal Blaze" = Bulbapedia "Ardent Obsidian")'}
 [pscustomobject]@{code='CSVE2C';num='122'; page='Battle_Party:_Shining_Dream_(ATCG)';                          ev='set list row: 122/207 Snorlax, Colorless. Simplified Chinese product 对战派对 耀梦 (Battle Party: Shining Dream), released July 18 / October 17 2025.'}
 [pscustomobject]@{code='CSVE1C';num='093'; page='Battle_Party:_Shared_Dream_(ATCG)';                           ev='set list row: 093/177 Snorlax, Colorless. Simplified Chinese product 对战派对 共梦 (Battle Party: Shared Dream), released February 28 / April 18 2025. Cardmarket calls it "Battle Party Dream Together".'}
)
$TYPE='Bulbapedia (fan wiki), Simplified Chinese (ATCG) set article'

function NN($n){ if($null -eq $n){return ''}; $s="$n".Trim()
  if($s -match '^[A-Za-z\-]*?(\d+)$'){ return [string][int]$Matches[1] }; return $s.ToUpper() }

$n=0;$ev=@()
foreach($row in $rows){
  foreach($u in $units){
    if($u.setCode -ne $row.code){continue}
    if((NN $u.number) -ne (NN $row.num)){continue}
    if($u.language -ne 'S-Chinese'){continue}
    if($u.status -in @('confirmed','contradicted')){continue}
    $u.status='confirmed'; $u.sourceUrl=$B+$row.page
    $u.evidence="Simplified Chinese set article; $($row.ev)"
    $u.sourceType=$TYPE; $u.checkedAt=(Get-Date -Format s)
    $ev+=[pscustomobject]@{unitId=$u.unitId;lang='S-Chinese';status='confirmed';source=$u.sourceUrl;evidence=$u.evidence;at=$u.checkedAt}
    $n++
  }
}
$units|ConvertTo-Json -Depth 4|Set-Content "$V\units.json" -Encoding utf8
if($ev){ $ev|ForEach-Object{$_|ConvertTo-Json -Compress}|Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='manual-atcg';completedAt=(Get-Date -Format s)}|ConvertTo-Json|Set-Content "$V\state.json" -Encoding utf8
Write-Host "manual ATCG findings applied: $n"
$units|Group-Object status|Sort-Object Count -Desc|Format-Table Count,Name -Auto
