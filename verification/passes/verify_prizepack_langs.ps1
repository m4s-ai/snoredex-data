$ErrorActionPreference='Stop'
$V=Split-Path -Parent $PSScriptRoot
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json
$B='https://bulbapedia.bulbagarden.net/wiki/'
$TYPE='Bulbapedia (fan wiki), Prize Pack Series article, "In other languages" table'

# The series articles carry an official localized product name per language.
# A localized product name evidences distribution in that language.
# Portuguese is absent from both tables - left open rather than contradicted,
# because a Langtable omission is not proof of non-release.
$rules=@(
 [pscustomobject]@{code='PPS1 VIV'; page='Play!_Pok%C3%A9mon_Prize_Pack_Series_One_(TCG)';
   langs=@('French','German','Italian','Spanish')
   ev='Series One official localized names: fr "Play! Pokemon Packs Recompense Premiere Serie", de "Play! Pokemon Preispack Serie 1", it "Play! Pokemon Buste Premio Prima Serie", es "Play! Pokemon Paquetes de Premio Serie 1"'}
 [pscustomobject]@{code='PPS3 LOR'; page='Play!_Pok%C3%A9mon_Prize_Pack_Series_Three_(TCG)';
   langs=@('French','German','Italian','Spanish')
   ev='Series Three official localized names: fr "Play! Pokemon Packs Recompense Troisieme Serie", de "Play! Pokemon Preispack Serie 3", it "Play! Pokemon Buste Premio Terza Serie", es "Play! Pokemon Paquetes de Premio Serie 3"'}
)
$n=0;$ev=@()
foreach($r in $rules){
  foreach($u in $units){
    if($u.setCode -ne $r.code){continue}
    if($u.language -notin $r.langs){continue}
    if($u.status -in @('confirmed','contradicted')){continue}
    $u.status='confirmed'; $u.sourceUrl=$B+$r.page; $u.sourceType=$TYPE; $u.evidence=$r.ev
    $u.checkedAt=(Get-Date -Format s)
    if($u.PSObject.Properties.Name -contains 'manualReason'){ $u.manualReason=$null }
    $ev+=[pscustomobject]@{unitId=$u.unitId;lang=$u.language;status='confirmed';source=$u.sourceUrl;evidence=$u.evidence;at=$u.checkedAt}
    $n++
  }
}
$units|ConvertTo-Json -Depth 4|Set-Content "$V\units.json" -Encoding utf8
if($ev){ $ev|ForEach-Object{$_|ConvertTo-Json -Compress}|Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='prizepack-langs';completedAt=(Get-Date -Format s)}|ConvertTo-Json|Set-Content "$V\state.json" -Encoding utf8
Write-Host "prize-pack language units confirmed: $n"
$units|Group-Object status|Sort-Object Count -Desc|Format-Table Count,Name -Auto
