$ErrorActionPreference='Stop'
$V="C:\redacted\Claude\snorlax-cardmarket\verification"
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json
$SRC='https://bulbapedia.bulbagarden.net/wiki/List_of_Pok%C3%A9mon_Trading_Card_Game_expansions_in_other_languages'
$JU ='https://bulbapedia.bulbagarden.net/wiki/Jungle_(TCG)'
$TYPE='Bulbapedia (fan wiki), cross-language expansion index'

# IMPORTANT: only positive ("Yes") cells are used. For Western-language columns a blank cell is NOT
# evidence of non-release - it usually means the localized set name equals the English one.
# (Proof: the index leaves Jungle/Portuguese blank, while the Jungle article states Portuguese was released.)
$T=@(
 [pscustomobject]@{code='JU';  langs=@('French','German','Italian','Spanish')}
 [pscustomobject]@{code='GEN'; langs=@('French','German','Italian','Spanish','Portuguese')}
 [pscustomobject]@{code='RR';  langs=@('French','German','Italian')}
 [pscustomobject]@{code='HIF'; langs=@('French','German','Italian','Spanish')}
 [pscustomobject]@{code='DP';  langs=@('French','German','Italian','Spanish','Portuguese')}
 [pscustomobject]@{code='CL';  langs=@('French','German','Italian')}
 [pscustomobject]@{code='SK';  langs=@('German')}
 [pscustomobject]@{code='TRR'; langs=@('Portuguese')}
 [pscustomobject]@{code='FL';  langs=@('French','German','Italian')}
 [pscustomobject]@{code='DF';  langs=@('French','German','Italian')}
)
$n=0;$ev=@()
foreach($row in $T){
  foreach($u in $units){
    if($u.setCode -ne $row.code){continue}
    if($u.status -in @('confirmed','contradicted')){continue}
    if($u.language -notin $row.langs){continue}
    $u.status='confirmed'; $u.sourceType=$TYPE; $u.sourceUrl=$SRC
    $u.evidence="expansion $($u.setName) ($($u.setCode)) is listed with a $($u.language) release in the cross-language expansion index (set-level evidence)"
    $u.checkedAt=(Get-Date -Format s)
    $ev+=[pscustomobject]@{unitId=$u.unitId;lang=$u.language;status='confirmed';source=$SRC;evidence=$u.evidence;at=$u.checkedAt}
    $n++
  }
}
# Jungle Portuguese comes from the expansion article, which states the print languages explicitly
foreach($u in $units){
  if($u.setCode -eq 'JU' -and $u.language -eq 'Portuguese' -and $u.status -notin @('confirmed','contradicted')){
    $u.status='confirmed'; $u.sourceType='Bulbapedia (fan wiki), expansion article'; $u.sourceUrl=$JU
    $u.evidence='Jungle print languages: released in English, Dutch, German, French, Italian, Spanish and Portuguese'
    $u.checkedAt=(Get-Date -Format s)
    $ev+=[pscustomobject]@{unitId=$u.unitId;lang='Portuguese';status='confirmed';source=$JU;evidence=$u.evidence;at=$u.checkedAt}
    $n++
  }
}
$units|ConvertTo-Json -Depth 4|Set-Content "$V\units.json" -Encoding utf8
if($ev){ $ev|ForEach-Object{$_|ConvertTo-Json -Compress}|Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='west-setlevel';completedAt=(Get-Date -Format s)}|ConvertTo-Json|Set-Content "$V\state.json" -Encoding utf8
Write-Host "confirmed: $n"
$units|Group-Object status|Sort-Object Count -Desc|Format-Table Count,Name -Auto
