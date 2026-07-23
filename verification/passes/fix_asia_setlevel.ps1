$ErrorActionPreference='Stop'
$V=Split-Path -Parent $PSScriptRoot
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json
$SRC='https://bulbapedia.bulbagarden.net/wiki/List_of_Pok%C3%A9mon_Trading_Card_Game_expansions_in_other_languages'
$TYPE='Bulbapedia (fan wiki), cross-language expansion index (raw wikitext via MediaWiki API)'

# CORRECTION. The index uses two different table shapes:
#   modern sections : Japanese | English | Traditional Chinese | Indonesian | Thai | Korean
#   older  sections : Japanese | English | Korean            <- no TC/ID/TH column at all
# An earlier pass treated a missing Traditional Chinese cell in an OLDER section as
# evidence of non-release. That was wrong: the column does not exist there.
# Only an explicit em-dash (often "colspan=3 | -") is evidence of non-release.

$M=@{}
function S($code,$tc,$idn,$th,$ko){ $M[$code]=@{'T-Chinese'=$tc;'Indonesian'=$idn;'Thai'=$th;'Korean'=$ko} }
#  code    TC        ID        TH        KO          (modern 6-column rows, values read from wikitext)
S 's10a'  'yes'     'yes'     'yes'     'yes'
S 's8b'   'yes'     'yes'     'yes'     'yes'
S 'sv2a'  'yes'     'yes'     'yes'     'yes'
S 'sv4a'  'yes'     'yes'     'yes'     'yes'
S 'sv5a'  'yes'     'no'      'yes'     'yes'
S 'sv9'   'yes'     'no'      'no'      'yes'
S 'm2a'   'yes'     'yes'     'yes'     'yes'
S 'm3'    'yes'     'no'      'no'      'yes'
S 's2'    'no'      'no'      'no'      'yes'   # explicit "colspan=3 | -"
S 's1H'   'no'      'no'      'no'      'yes'   # explicit "colspan=3 | -"
#  older 3-column rows: Korean decidable, everything else UNKNOWN
S 'sm9'   'unknown' 'unknown' 'unknown' 'yes'
S 'sm10'  'unknown' 'unknown' 'unknown' 'yes'
S 'XY2'   'unknown' 'unknown' 'unknown' 'yes'
S 'BW7'   'unknown' 'unknown' 'unknown' 'yes'
S 'XY10'  'unknown' 'unknown' 'unknown' 'yes'

$rev=0;$conf=0;$contra=0;$ev=@()
foreach($u in $units){
  if(-not $M.ContainsKey($u.setCode)){ continue }
  $row=$M[$u.setCode]
  if(-not $row.ContainsKey($u.language)){ continue }
  $val=$row[$u.language]

  if($val -eq 'unknown'){
    if($u.status -eq 'contradicted'){
      $u.status='pending'; $u.sourceUrl=$null; $u.sourceType=$null
      $u.evidence="REVERTED: earlier contradiction was unsafe - the expansion index section covering $($u.setName) has no $($u.language) column at all, so an empty cell is not evidence of non-release"
      $u.checkedAt=(Get-Date -Format s); $rev++
      $ev+=[pscustomobject]@{unitId=$u.unitId;lang=$u.language;status='pending';source=$SRC;evidence=$u.evidence;at=$u.checkedAt}
    }
    continue
  }
  if($u.status -in @('confirmed','contradicted')){ continue }
  if($val -eq 'yes'){
    $u.status='confirmed'
    $u.evidence="cross-language expansion index row for $($u.setName) carries a localized $($u.language) set name (set-level evidence)"
    $conf++
  } else {
    $u.status='contradicted'
    $u.evidence="cross-language expansion index row for $($u.setName) shows an explicit em-dash in the $($u.language) column, i.e. no $($u.language) release"
    $contra++
  }
  $u.sourceType=$TYPE; $u.sourceUrl=$SRC; $u.checkedAt=(Get-Date -Format s)
  $ev+=[pscustomobject]@{unitId=$u.unitId;lang=$u.language;status=$u.status;source=$SRC;evidence=$u.evidence;at=$u.checkedAt}
}
$units|ConvertTo-Json -Depth 4|Set-Content "$V\units.json" -Encoding utf8
if($ev){ $ev|ForEach-Object{$_|ConvertTo-Json -Compress}|Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='asia-setlevel-corrected';completedAt=(Get-Date -Format s)}|ConvertTo-Json|Set-Content "$V\state.json" -Encoding utf8
Write-Host "unsafe contradictions reverted: $rev"
Write-Host "newly confirmed: $conf   newly contradicted: $contra"
$units|Group-Object status|Sort-Object Count -Desc|Format-Table Count,Name -Auto
