$ErrorActionPreference='Stop'
$V="C:\redacted\Claude\snorlax-cardmarket\verification"
$A="$V\cache\asia"
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json
$LOC=@{ 'tw'='T-Chinese'; 'th'='Thai'; 'id'='Indonesian' }

function NC($s){ if(-not $s){return ''}; ($s.ToUpper() -replace '[^A-Z0-9]','') }
function NN($n){ if($null -eq $n -or "$n" -eq ''){return ''}; $s="$n".Trim()
  if($s -match '^[A-Za-z\-]*?(\d+)$'){ return [string][int]$Matches[1] }; return $s.ToUpper() }

# Cardmarket setCode (normalised) -> official Asia expansion code (normalised)
$ALIAS=@{}
$ALIAS['SI100']='SI'          # Start Deck 100
$ALIAS['PKMTCHSP']='SP'       # Cardmarket files the TW promo under "Traditional Chinese Products"
$ALIAS['SVPTH']='SVP'         # Cardmarket splits SV promos per region; the official DB does not
$ALIAS['SVPID']='SVP'

$recs=@()
foreach($f in (Get-ChildItem $A -Filter '*_*.json')){
  if($f.Name -eq 'ids.json'){continue}
  $r=Get-Content $f.FullName -Raw -Encoding utf8|ConvertFrom-Json
  if($r.expansion -and $r.number){ $recs+=$r }
}
$idx=@{}
foreach($r in $recs){
  $lang=$LOC[$r.loc]; if(-not $lang){continue}
  $idx["$lang|$(NC $r.expansion)|$(NN $r.number)"]=$r
}
Write-Host "indexed official Asia records: $($idx.Count)"

$n=0;$ev=@()
foreach($u in $units){
  if($u.status -in @('confirmed','contradicted')){continue}
  $code=NC $u.setCode
  if($ALIAS.ContainsKey($code)){ $code=$ALIAS[$code] }
  $r=$idx["$($u.language)|$code|$(NN $u.number)"]
  if(-not $r){ continue }
  $u.status='confirmed'
  $u.sourceType='Official Pokemon Asia card database (asia.pokemon-card.com)'
  $u.sourceUrl=$r.url
  $u.evidence="official $($r.loc) entry: expansion=$($r.expansion) collectorNumber=$($r.number)"
  $u.checkedAt=(Get-Date -Format s)
  $ev+=[pscustomobject]@{unitId=$u.unitId;lang=$u.language;status='confirmed';source=$r.url;evidence=$u.evidence;at=$u.checkedAt}
  $n++
}
$units|ConvertTo-Json -Depth 4|Set-Content "$V\units.json" -Encoding utf8
if($ev){ $ev|ForEach-Object{$_|ConvertTo-Json -Compress}|Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='asia-official-2';completedAt=(Get-Date -Format s)}|ConvertTo-Json|Set-Content "$V\state.json" -Encoding utf8
Write-Host "newly confirmed via official Asia DB: $n"
$units|Group-Object status|Sort-Object Count -Desc|Format-Table Count,Name -Auto
