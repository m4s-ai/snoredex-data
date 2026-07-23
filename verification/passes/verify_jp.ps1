$ErrorActionPreference='Stop'
$V=Split-Path -Parent $PSScriptRoot
$J="$V\cache\jp"
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json

function NC($s){ if(-not $s){return ''}; ($s.ToUpper() -replace '[^A-Z0-9]','') }
function NN($n){ if($null -eq $n -or "$n" -eq ''){return ''}; $s="$n".Trim()
  if($s -match '^[A-Za-z\-]*?(\d+)$'){ return [string][int]$Matches[1] }; return $s.ToUpper() }

# Cardmarket setCode (normalised) -> official JP setCode (normalised)
$ALIAS=@{}
$ALIAS['SI100']='SI'; $ALIAS['MP1']='MP'; $ALIAS['PT2']='DPT2B'
$ALIAS['HSZ']='HSZP'; $ALIAS['XY10']='XY10B'; $ALIAS['BW7']='BW7B'

$recs=@()
foreach($f in (Get-ChildItem $J -Filter 'card_*.json')){
  $rec=Get-Content $f.FullName -Raw -Encoding utf8|ConvertFrom-Json
  # drop Munchlax (ゴンベ) - the official search matches it fuzzily
  if($rec.name -match 'ゴンベ' -and $rec.name -notmatch 'カビゴン'){ continue }
  if(-not $rec.number){ continue }   # promo pages without a collector number cannot be pinned
  $recs += $rec
}
Write-Host "usable official JP records (numbered, Snorlax family): $($recs.Count)"

$idx=@{}
foreach($rec in $recs){ $idx["$(NC $rec.setCode)|$(NN $rec.number)"]=$rec }

$hit=0; $ev=@(); $artistAdds=0
foreach($u in $units){
  if($u.language -ne 'Japanese'){ continue }
  if($u.status -in @('confirmed','contradicted')){ continue }
  $code=NC $u.setCode
  if($ALIAS.ContainsKey($code)){ $code=$ALIAS[$code] }
  $rec=$idx["$code|$(NN $u.number)"]
  if(-not $rec){ continue }
  $u.status='confirmed'
  $u.sourceType='Official Pokemon Japan card database (pokemon-card.com)'
  $u.sourceUrl=$rec.url
  $u.evidence="official JP entry: set=$($rec.setCode) number=$($rec.number)/$($rec.setTotal) name=$($rec.name) illustrator=$($rec.illustrator)"
  $u.checkedAt=(Get-Date -Format s)
  if(-not $u.artist -and $rec.illustrator){ $u.artist=$rec.illustrator; $artistAdds++ }
  $ev+=[pscustomobject]@{unitId=$u.unitId;lang='Japanese';source=$rec.url;evidence=$u.evidence;at=$u.checkedAt}
  $hit++
}
$units|ConvertTo-Json -Depth 4|Set-Content "$V\units.json" -Encoding utf8
if($ev){ $ev|ForEach-Object{$_|ConvertTo-Json -Compress}|Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='jp-official';completedAt=(Get-Date -Format s);confirmed=$hit}|ConvertTo-Json|Set-Content "$V\state.json" -Encoding utf8

# export official JP artist table (independent of the English artist source)
$recs | Select-Object setCode,number,name,illustrator,url | ConvertTo-Json -Depth 3 |
  Set-Content "$V\artists_official_jp.json" -Encoding utf8

Write-Host "newly confirmed (Japanese): $hit"
Write-Host "artists filled from official JP source: $artistAdds"
$units|Group-Object status|Sort-Object Count -Desc|Format-Table Count,Name -Auto
