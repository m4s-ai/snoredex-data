$ErrorActionPreference='Stop'
$V="C:\redacted\Claude\snorlax-cardmarket\verification"
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json
$B='https://bulbapedia.bulbagarden.net/wiki/'
$T151='Bulbapedia (fan wiki), 151 (TCG) expansion article'
$TSET='Bulbapedia (fan wiki), expansion set list'

# Cardmarket "x<SET>" = special editions of cards from <SET>: mirror-holo ball patterns or retail stamps.
# Each case below is pinned to a quoted sentence or set-list row.

$Q151='151 (TCG): "In the Japanese, Korean and Traditional Chinese subsets ... common, uncommon, and rare cards have Mirror Holofoil variants featuring a Poke Ball pattern; or, rarely, a Master Ball pattern. Thai and Indonesian booster packs contain five cards with no guarantees of Holofoil cards, and has no Mirror Holofoil prints."'
$QM2A='MEGA Dream ex (TCG): "It also introduces a new Mirror Holofoil Energy pattern and various Poke Ball patterns ... Trainer''s Pokemon and Mythical Pokemon can have a Mirror Holofoil featuring a regular Poke Ball". Hop''s Snorlax is a Trainer''s Pokemon.'
$QJTG='Journey Together (TCG) set list records exactly three stamped printings of 117/159 Hop''s Snorlax: "Journey Together" stamp (Malaysia, Philippines, Singapore), "GameStop" stamp (USA, Canada), "EBGames" stamp (Australia, New Zealand) - all English-language retail markets.'
$QPRE='Prismatic Evolutions (TCG) set list: 076/131 Snorlax ex, plus a [Jumbo] printing, both "Snorlax ex & Blissey ex Special Collection exclusive with Prismatic Evolutions stamp".'

$rules=@(
 # xsv2a - Master Ball / Poke Ball mirror holo
 [pscustomobject]@{code='xsv2a'; langs=@('Japanese','Korean','T-Chinese'); status='confirmed';    page='151_(TCG)';                  type=$T151; ev="mirror-holo (Poke Ball / Master Ball) printing of Pokemon Card 151 #143. $Q151"}
 [pscustomobject]@{code='xsv2a'; langs=@('Indonesian','Thai');            status='contradicted'; page='151_(TCG)';                  type=$T151; ev="Thai and Indonesian print runs carry no Mirror Holofoil variants at all, so this special edition cannot exist in them. $Q151"}
 # xm2a - Poke Ball mirror holo for Trainer's Pokemon
 [pscustomobject]@{code='xm2a';  langs=@('Japanese');                     status='confirmed';    page='MEGA_Dream_ex_(TCG)';        type=$TSET; ev="mirror-holo (Poke Ball) printing of MEGA Dream ex #136. $QM2A"}
 # xJTG - three retail stamps, all English-market
 [pscustomobject]@{code='xJTG';  langs=@('English');                      status='confirmed';    page='Journey_Together_(TCG)';     type=$TSET; ev=$QJTG}
 [pscustomobject]@{code='xJTG';  langs=@('French','German','Italian','Spanish','Portuguese'); status='contradicted'; page='Journey_Together_(TCG)'; type=$TSET; ev="every documented printing of this stamped card was distributed in an English-language retail market; no localized run is recorded. $QJTG"}
 # xPRE - Special Collection stamp + Jumbo
 [pscustomobject]@{code='xPRE';  langs=@('English');                      status='confirmed';    page='Prismatic_Evolutions_(TCG)'; type=$TSET; ev=$QPRE}
)

$c=0;$x=0;$ev=@()
foreach($r in $rules){
  foreach($u in $units){
    if($u.setCode -ne $r.code){continue}
    if($u.language -notin $r.langs){continue}
    if($u.status -in @('confirmed','contradicted')){continue}
    $u.status=$r.status; $u.sourceUrl=$B+$r.page; $u.sourceType=$r.type; $u.evidence=$r.ev
    $u.checkedAt=(Get-Date -Format s)
    if($u.PSObject.Properties.Name -contains 'manualReason'){ $u.manualReason=$null }
    if($r.status -eq 'confirmed'){$c++}else{$x++}
    $ev+=[pscustomobject]@{unitId=$u.unitId;lang=$u.language;status=$u.status;source=$u.sourceUrl;evidence=$u.evidence;at=$u.checkedAt}
  }
}
$units|ConvertTo-Json -Depth 4|Set-Content "$V\units.json" -Encoding utf8
if($ev){ $ev|ForEach-Object{$_|ConvertTo-Json -Compress}|Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='additionals';completedAt=(Get-Date -Format s)}|ConvertTo-Json|Set-Content "$V\state.json" -Encoding utf8
Write-Host "Additionals resolved - confirmed: $c   contradicted: $x"
$units|Group-Object status|Sort-Object Count -Desc|Format-Table Count,Name -Auto
