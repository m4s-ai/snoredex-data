$ErrorActionPreference='Stop'
$V=Split-Path -Parent $PSScriptRoot
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json
$LANG=[ordered]@{'English'='en';'French'='fr';'German'='de';'Spanish'='es';'Italian'='it';'Portuguese'='pt';
 'Dutch'='nl';'Polish'='pl';'Russian'='ru';'Japanese'='ja';'Korean'='ko';'T-Chinese'='zh-tw';
 'S-Chinese'='zh-cn';'Indonesian'='id';'Thai'='th'}
$SEED=@{'JU'='base2';'B2'='base4';'WP'='basep';'BCR'='bw7';'PLS'='bw8';'CL'='col1';'DP'='dp1';'SK'='ecard3';
 'DF'='ex15';'FL'='ex6';'TRR'='ex7';'GEN'='g1';'GH'='gym1';'LC'='lc';'POR'='me03';'RR'='pl2';'UNB'='sm10';
 'HIF'='sm115';'TEU'='sm9';'SM'='smp';'MEW'='sv03.5';'PAR'='sv04';'PAF'='sv04.5';'TWM'='sv06';'SSP'='sv08';
 'PRE'='sv08.5';'JTG'='sv09';'SVP'='svp';'SSH'='swsh1';'PGO'='swsh10.5';'CRZ'='swsh12.5';
 'RCL'='swsh2';'VIV'='swsh4';'CRE'='swsh6';'FST'='swsh8';'SWSH'='swshp';'KSS'='xy0';'FCO'='xy10';
 'FLF'='xy2';'BKT'='xy8';'XYPR'='xyp'}
function Norm($n){ if($null -eq $n){return ''}; $s="$n".Trim()
  if($s -match '^[A-Za-z\-]*?(\d+)$'){ return [string][int]$Matches[1] }; return $s.ToUpper() }
function NN($s){ if(-not $s){return ''}
  ($s.ToLower() -replace '[éèê]','e' -replace '&',' and ' -replace 'pok.mon','pokemon' -replace '[^a-z0-9]','') }

$idx=@{}; $setNameOf=@{}; $byNum=@{}
foreach($l in $LANG.Values){
  $idx[$l]=@{}
  $sf="$V\cache\full_sets_$l.json"
  if(Test-Path $sf){ foreach($s in (Get-Content $sf -Raw -Encoding utf8|ConvertFrom-Json)){ $setNameOf["$l|$($s.id)"]=$s.name } }
  $cf="$V\cache\full_cards_$l.json"
  if(-not (Test-Path $cf)){continue}
  foreach($c in (Get-Content $cf -Raw -Encoding utf8|ConvertFrom-Json)){
    $i=$c.id; if(-not $i){continue}; $p=$i.LastIndexOf('-'); if($p -lt 1){continue}
    $sid=$i.Substring(0,$p); $nl=Norm $c.localId
    $idx[$l]["$sid|$nl"]=$c
    if(-not $byNum.ContainsKey($nl)){ $byNum[$nl]=New-Object System.Collections.ArrayList }
    [void]$byNum[$nl].Add([pscustomobject]@{lang=$l;setId=$sid})
  }
}
if(Test-Path "$V\cache\full_cards_pt-br.json"){ foreach($c in (Get-Content "$V\cache\full_cards_pt-br.json" -Raw -Encoding utf8|ConvertFrom-Json)){
    $i=$c.id;$p=$i.LastIndexOf('-'); if($p -lt 1){continue}; $sid=$i.Substring(0,$p)
    if(-not $idx['pt']["$sid|$(Norm $c.localId)"]){$idx['pt']["$sid|$(Norm $c.localId)"]=$c} } }
Write-Host "index built"

$groups = $units | Group-Object {"$($_.setCode)|$($_.number)|$($_.variant)"}
$resolved=@{}
foreach($g in $groups){
  $u=$g.Group[0]
  if($SEED.ContainsKey($u.setCode)){ $resolved[$g.Name]=$SEED[$u.setCode]; continue }
  $nl=Norm $u.number
  $cands=$byNum[$nl]
  if($cands){
    $votes=@{}
    foreach($c in $cands){
      $sn=$setNameOf["$($c.lang)|$($c.setId)"]
      if($sn -and (NN $sn) -eq (NN $u.setName)){ if(-not $votes.ContainsKey($c.setId)){$votes[$c.setId]=0}; $votes[$c.setId]++ }
    }
    if($votes.Count){ $resolved[$g.Name]=($votes.GetEnumerator()|Sort-Object Value -Desc|Select-Object -First 1).Key; continue }
    foreach($c in $cands){ if($c.setId -ieq $u.setCode){ $resolved[$g.Name]=$c.setId; break } }
  }
}
Write-Host "resolved setIds: $($resolved.Count) / $($groups.Count) distinct cards"

$hit=0; $ev=@()
foreach($u in $units){
  if($u.status -eq 'confirmed'){continue}
  $lg=$LANG[$u.language]; if(-not $lg){ $u.status='no-source-available'; continue }
  $sid=$resolved["$($u.setCode)|$($u.number)|$($u.variant)"]; if(-not $sid){continue}
  $c=$idx[$lg]["$sid|$(Norm $u.number)"]
  if($c){
    $u.status='confirmed'; $u.sourceType='TCGdex API (open card database)'
    $u.sourceUrl="https://api.tcgdex.net/v2/$lg/cards/$($c.id)"
    $u.evidence="$lg card '$($c.name)' id=$($c.id)"; $u.checkedAt=(Get-Date -Format s)
    $ev+=[pscustomobject]@{unitId=$u.unitId;lang=$u.language;source=$u.sourceUrl;name=$c.name;at=$u.checkedAt}; $hit++
  }
}
$units|ConvertTo-Json -Depth 4|Set-Content "$V\units.json" -Encoding utf8
if($ev){ $ev|ForEach-Object{$_|ConvertTo-Json -Compress}|Add-Content "$V\evidence.jsonl" -Encoding utf8 }
$resolved.GetEnumerator()|ForEach-Object{[pscustomobject]@{card=$_.Key;tcgdexSetId=$_.Value}}|ConvertTo-Json|Set-Content "$V\cache\setid_map.json" -Encoding utf8
@{phase='tcgdex-full';completedAt=(Get-Date -Format s)}|ConvertTo-Json|Set-Content "$V\state.json" -Encoding utf8
Write-Host "newly confirmed: $hit"
$units|Group-Object status|Format-Table Count,Name -Auto
$units|Where-Object{$_.status -ne 'confirmed'}|Group-Object language|Sort-Object Count -Desc|Format-Table Count,Name -Auto
