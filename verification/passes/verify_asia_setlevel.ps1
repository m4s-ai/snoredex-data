$ErrorActionPreference='Stop'
$V="C:\Users\marku\Claude\snorlax-cardmarket\verification"
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json
$SRC='https://bulbapedia.bulbagarden.net/wiki/List_of_Pok%C3%A9mon_Trading_Card_Game_expansions_in_other_languages'
$TYPE='Bulbapedia (fan wiki), cross-language expansion index'

# setCode -> language -> yes|no   (omitted = not listed on the page, stays open)
$M=@{}
function Set-M($code,$ko,$tc,$idn,$th,$koName){
  $M[$code]=@{ 'Korean'=$ko; 'T-Chinese'=$tc; 'Indonesian'=$idn; 'Thai'=$th; 'koName'=$koName }
}
#          code     KO    TC    ID    TH    Korean name
Set-M 's1H'   'yes' 'no'  ''    ''    '실드'
Set-M 's10a'  'yes' 'yes' ''    ''    '다크판타스마'
Set-M 'sm9'   'yes' 'no'  ''    ''    '태그볼트'
Set-M 's8b'   'yes' 'yes' ''    ''    'VMAX 클라이맥스'
Set-M 's5a'   'yes' 'yes' ''    ''    '쌍벽의 파이터'
Set-M 's2'    'yes' 'no'  ''    ''    '반역크래시'
Set-M 'XY2'   'yes' 'no'  ''    ''    '와일드 블레이즈'
Set-M 'sm10'  'yes' 'no'  ''    ''    '더블블레이즈'
Set-M 'BW7'   'yes' 'no'  ''    ''    '플라스마게일'
Set-M 'sv2a'  'yes' 'yes' 'yes' 'yes' ''
Set-M 'sv4a'  'yes' 'yes' 'yes' 'yes' ''
Set-M 'sv5a'  'yes' 'no'  'no'  'yes' ''
Set-M 'sv9'   'yes' 'yes' 'no'  'no'  ''
Set-M 'm2a'   'yes' 'yes' 'yes' 'yes' ''
Set-M 'm3'    'yes' 'yes' 'no'  'no'  ''
Set-M 'XY10'  'yes' 'no'  'no'  'no'  ''

$conf=0;$contra=0;$ev=@()
foreach($u in $units){
  if($u.status -in @('confirmed','contradicted')){ continue }
  if(-not $M.ContainsKey($u.setCode)){ continue }
  $row=$M[$u.setCode]
  if(-not $row.ContainsKey($u.language)){ continue }
  $val=$row[$u.language]
  if($val -eq 'yes'){
    $u.status='confirmed'; $u.sourceType=$TYPE; $u.sourceUrl=$SRC
    $nm=if($u.language -eq 'Korean' -and $row['koName']){" as `"$($row['koName'])`""}else{""}
    $u.evidence="expansion $($u.setName) ($($u.setCode)) is listed with a $($u.language) release$nm in the cross-language expansion index (set-level evidence)"
    $conf++
  } elseif($val -eq 'no'){
    $u.status='contradicted'; $u.sourceType=$TYPE; $u.sourceUrl=$SRC
    $u.evidence="expansion $($u.setName) ($($u.setCode)) has NO $($u.language) entry in the cross-language expansion index, so no $($u.language) printing of this card should exist"
    $contra++
  } else { continue }
  $u.checkedAt=(Get-Date -Format s)
  $ev+=[pscustomobject]@{unitId=$u.unitId;lang=$u.language;status=$u.status;source=$SRC;evidence=$u.evidence;at=$u.checkedAt}
}
$units|ConvertTo-Json -Depth 4|Set-Content "$V\units.json" -Encoding utf8
if($ev){ $ev|ForEach-Object{$_|ConvertTo-Json -Compress}|Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='asia-setlevel';completedAt=(Get-Date -Format s)}|ConvertTo-Json|Set-Content "$V\state.json" -Encoding utf8
Write-Host "confirmed: $conf   contradicted: $contra"
$units|Group-Object status|Sort-Object Count -Desc|Format-Table Count,Name -Auto
