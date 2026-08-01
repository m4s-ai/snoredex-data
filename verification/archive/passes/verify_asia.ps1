$ErrorActionPreference='Stop'
$V=Split-Path -Parent $PSScriptRoot
$A="$V\cache\asia"
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json

# official Asia locale -> Cardmarket language
$LOC=@{ 'tw'='T-Chinese'; 'th'='Thai'; 'id'='Indonesian' }

function Norm($n){ if($null -eq $n){return ''}; $s="$n".Trim()
  if($s -match '^[A-Za-z\-]*?(\d+)$'){ return [string][int]$Matches[1] }; return $s.ToUpper() }

$recs=@()
foreach($f in (Get-ChildItem $A -Filter '*_*.json')){
  if($f.Name -eq 'ids.json'){continue}
  $r=Get-Content $f.FullName -Raw -Encoding utf8|ConvertFrom-Json
  if($r.expansion -and $r.number){ $recs += $r }
}
Write-Host "usable official records: $($recs.Count)"

# index: "LANG|EXPANSION|NORMNUM" -> record
$idx=@{}
foreach($r in $recs){
  $lang=$LOC[$r.loc]; if(-not $lang){continue}
  $idx["$lang|$($r.expansion.ToUpper())|$(Norm $r.number)"]=$r
}

$hit=0; $ev=@()
foreach($u in $units){
  if($u.status -eq 'confirmed'){continue}
  $k="$($u.language)|$($u.setCode.ToUpper())|$(Norm $u.number)"
  $r=$idx[$k]
  if($r){
    $u.status='confirmed'
    $u.sourceType='Official Pokemon Asia card database (asia.pokemon-card.com)'
    $u.sourceUrl=$r.url
    $u.evidence="official $($r.loc) entry, expansion=$($r.expansion) collectorNumber=$($r.number)"
    $u.checkedAt=(Get-Date -Format s)
    $ev+=[pscustomobject]@{unitId=$u.unitId;lang=$u.language;source=$u.sourceUrl;evidence=$u.evidence;at=$u.checkedAt}
    $hit++
  }
}
$units|ConvertTo-Json -Depth 4|Set-Content "$V\units.json" -Encoding utf8
if($ev){ $ev|ForEach-Object{$_|ConvertTo-Json -Compress}|Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='asia-official';completedAt=(Get-Date -Format s);confirmed=$hit}|ConvertTo-Json|Set-Content "$V\state.json" -Encoding utf8
Write-Host "newly confirmed via official Asia DB: $hit"
$units|Group-Object status|Format-Table Count,Name -Auto
$units|Where-Object{$_.status -ne 'confirmed'}|Group-Object language|Sort-Object Count -Desc|Format-Table Count,Name -Auto
