$ErrorActionPreference='Stop'
$V=Split-Path -Parent $PSScriptRoot
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json
$TYPE='Bulbapedia (fan wiki), Play! Pokemon Prize Pack Series article'

# The Prize Pack series articles list the exact card, which evidences the printing itself.
# They do NOT state distribution languages, so only English is claimed here.
$P=@(
 [pscustomobject]@{code='PPS1 VIV'; url='https://bulbapedia.bulbagarden.net/wiki/Play!_Pok%C3%A9mon_Prize_Pack_Series_One_(TCG)';   ev='Prize Pack Series One card list contains row "131/185 Snorlax" (Vivid Voltage), Play! Pokemon stamped printing'}
 [pscustomobject]@{code='PPS3 LOR'; url='https://bulbapedia.bulbagarden.net/wiki/Play!_Pok%C3%A9mon_Prize_Pack_Series_Three_(TCG)'; ev='Prize Pack Series Three card list contains row "143/196 Snorlax, Rare Holo" (Lost Origin), Play! Pokemon stamped printing'}
)
$n=0;$ev=@()
foreach($row in $P){
  foreach($u in $units){
    if($u.setCode -ne $row.code){continue}
    if($u.language -ne 'English'){continue}
    if($u.status -in @('confirmed','contradicted')){continue}
    $u.status='confirmed'; $u.sourceType=$TYPE; $u.sourceUrl=$row.url; $u.evidence=$row.ev
    $u.checkedAt=(Get-Date -Format s)
    $ev+=[pscustomobject]@{unitId=$u.unitId;lang='English';status='confirmed';source=$row.url;evidence=$row.ev;at=$u.checkedAt}
    $n++
  }
}
$units|ConvertTo-Json -Depth 4|Set-Content "$V\units.json" -Encoding utf8
if($ev){ $ev|ForEach-Object{$_|ConvertTo-Json -Compress}|Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='prize-packs';completedAt=(Get-Date -Format s)}|ConvertTo-Json|Set-Content "$V\state.json" -Encoding utf8
Write-Host "prize-pack English units confirmed: $n"
$units|Group-Object status|Sort-Object Count -Desc|Format-Table Count,Name -Auto
