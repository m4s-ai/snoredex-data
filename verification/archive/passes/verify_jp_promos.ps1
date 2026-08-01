$ErrorActionPreference='Stop'
$V=Split-Path -Parent $PSScriptRoot
$J="$V\cache\jp"
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json

function NC($s){ if(-not $s){return ''}; ($s.ToUpper() -replace '[^A-Z0-9]','') }
$ALIAS=@{}
$ALIAS['DPP']='DPP'; $ALIAS['XYP']='XYP'; $ALIAS['SMP']='SMP'; $ALIAS['SP']='SP'
$ALIAS['BWP']='BWP'; $ALIAS['DP1']='DP1'; $ALIAS['MP1']='MP'

# Cardmarket card name -> Japanese name fragment on the official site
$JPNAME=@{}
$JPNAME['Snorlax']='カビゴン'
$JPNAME['Snorlax V']='カビゴンV'
$JPNAME['Snorlax VMAX']='カビゴンVMAX'
$JPNAME['Snorlax GX']='カビゴンGX'
$JPNAME['Snorlax ex']='カビゴンex'
$JPNAME["Hop's Snorlax"]='ホップのカビゴン'
$JPNAME['Snorlax Doll']='カビゴンドール'
$JPNAME["Rocket's Snorlax"]='R団のカビゴン'
$JPNAME['Snorlax Lv.X']='カビゴン'
$JPNAME['Snorlax Lv.37']='カビゴン'
$JPNAME['Snorlax Lv.35']='カビゴン'
$JPNAME['Snorlax Lv.40']='カビゴン'

# official records WITHOUT a collector number (promo pages)
$recs=@()
foreach($f in (Get-ChildItem $J -Filter 'card_*.json')){
  $r=Get-Content $f.FullName -Raw -Encoding utf8|ConvertFrom-Json
  if($r.number){ continue }
  if($r.name -match 'ゴンベ' -and $r.name -notmatch 'カビゴン'){ continue }
  $recs += $r
}
Write-Host "numberless official JP promo records: $($recs.Count)"

$n=0;$ev=@()
foreach($u in $units){
  if($u.language -ne 'Japanese'){continue}
  if($u.status -in @('confirmed','contradicted')){continue}
  $code=NC $u.setCode
  if($ALIAS.ContainsKey($code)){ $code=$ALIAS[$code] }
  $want=$JPNAME[$u.cardName]
  if(-not $want){ continue }
  $cands=@($recs | Where-Object { (NC $_.setCode) -eq $code })
  # LV.X pages are flagged by a level-up marker in the parsed name/illustrator field
  if($u.cardName -eq 'Snorlax Lv.X'){ $cands=@($cands|Where-Object{ $_.illustrator -match 'LV|レベルアップ' }) }
  elseif($u.cardName -like 'Snorlax Lv.*'){ $cands=@($cands|Where-Object{ $_.illustrator -notmatch 'LV|レベルアップ' }) }
  $cands=@($cands | Where-Object { $_.name -like "*$want*" })
  if($cands.Count -ne 1){ continue }   # only accept unambiguous matches
  $rec=$cands[0]
  $u.status='confirmed'
  $u.sourceType='Official Pokemon Japan card database (pokemon-card.com)'
  $u.sourceUrl=$rec.url
  $u.evidence="official JP promo entry: set=$($rec.setCode) name=$($rec.name) illustrator=$($rec.illustrator) (promo page carries no collector number; match is unambiguous by set + card name)"
  $u.checkedAt=(Get-Date -Format s)
  if(-not $u.artist -and $rec.illustrator){ $u.artist=$rec.illustrator }
  $ev+=[pscustomobject]@{unitId=$u.unitId;lang='Japanese';status='confirmed';source=$rec.url;evidence=$u.evidence;at=$u.checkedAt}
  $n++
}
$units|ConvertTo-Json -Depth 4|Set-Content "$V\units.json" -Encoding utf8
if($ev){ $ev|ForEach-Object{$_|ConvertTo-Json -Compress}|Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='jp-promos';completedAt=(Get-Date -Format s)}|ConvertTo-Json|Set-Content "$V\state.json" -Encoding utf8
Write-Host "JP promo units confirmed: $n"
$units|Group-Object status|Sort-Object Count -Desc|Format-Table Count,Name -Auto
