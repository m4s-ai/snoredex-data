$ErrorActionPreference='Stop'
$base=Split-Path -Parent $PSScriptRoot
$cards=Get-Content "$base\_cards_stage1.json" -Raw -Encoding utf8|ConvertFrom-Json
$src=Get-Content "$base\artists_pokemontcgio.json" -Raw -Encoding utf8|ConvertFrom-Json

function NN($n){ if(-not $n){return ''}; $s="$n".Trim()
  if($s -match '^(TG)(\d+)$'){ return "TG"+[int]$Matches[2] }
  $s = $s -replace '^(SWSH|SM|XY|SVP|PR)',''
  if($s -match '^\d+$'){ return [string][int]$s }
  return $s.ToUpper() }

# Cardmarket setCode -> pokemontcg.io ptcgoCode or setName
$MAP=@{
 'JU'='JU';'WP'='PR';'B2'='B2';'GH'='G1';'LC'='LC';'SK'='SK';'FL'='RG';'TRR'='TRR';'DF'='DF';
 'DP'='DP';'RR'='RR';'CL'='CL';'BCR'='BCR';'PLS'='PLS';'XYPR'='PR-XY';'KSS'='KSS';'FLF'='FLF';
 'BKT'='BKT';'GEN'='GEN';'FCO'='FCO';'SM'='PR-SM';'TEU'='TEU';'UNB'='UNB';'HIF'='HIF';
 'SWSH'='PR-SW';'SSH'='SSH';'RCL'='RCL';'VIV'='VIV';'CRE'='CRE';'FST'='FST';'PGO'='PGO';
 'CRZ'='CRZ';'TWM'='TWM';'SSP'='SSP';'PRE'='PRE';'JTG'='JTG';'POR'='POR';'SVP'='PR-SV';
 'MEW'='@151';'PAR'='@Paradox Rift';'PAF'='@Paldean Fates';'LOR'='LOR'
}
# index source by (setKey, normNumber)
$idx=@{}
foreach($s in $src){
  $keys=@()
  if($s.ptcgoCode){ $keys+=$s.ptcgoCode }
  $keys+= '@'+$s.setName
  foreach($k in $keys){ $idx["$k|$(NN $s.number)"]=$s }
}
# LOR Trainer Gallery
foreach($s in $src){ if($s.setName -eq 'Lost Origin Trainer Gallery'){ $idx["LOR|$(NN $s.number)"]=$s } }
# SVP 184 lives under "Scarlet & Violet Promos"
foreach($s in $src){ if($s.setName -eq 'Scarlet & Violet Promos'){ $idx["PR-SV|$(NN $s.number)"]=$s } }

function Lookup($setCode,$number){
  if(-not $setCode){return $null}
  $sc=$setCode.Trim()
  if($MAP.ContainsKey($sc)){ $k=$MAP[$sc]; $hit=$idx["$k|$(NN $number)"]; if($hit){return $hit} }
  return $null
}

$byUrlNum=@{}
foreach($c in $cards){ $byUrlNum["$($c.setCode)|$(NN $c.number)"]=$c }

# pass 1: direct
$direct=0
foreach($c in $cards){
  $hit=Lookup $c.setCode $c.number
  if($hit){ $c.artist=$hit.artist; $c.artistSource='pokemontcg.io (direct set+number match)'; $direct++ }
}
# pass 2: explicit reprint reference encoded in Cardmarket number, e.g. "VIV 131" / "LOR 143" / "JTG 117"
$rep=0
foreach($c in $cards){
  if($c.artist){continue}
  if("$($c.number)" -match '^([A-Za-z0-9\-]+)\s+(\S+)$'){
    $hit=Lookup $Matches[1] $Matches[2]
    if($hit){ $c.artist=$hit.artist; $c.artistSource="reprint of $($Matches[1]) $($Matches[2])"; $rep++ }
  }
}
# pass 3: URL-encoded reprint reference e.g. .../Battle-Academy-2020/Snorlax-HIF50
$urlref=0
foreach($c in $cards){
  if($c.artist){continue}
  if($c.productUrl -match '/[A-Za-z\-]*?-([A-Z]{2,5})(\d{1,3})$'){
    $hit=Lookup $Matches[1] $Matches[2]
    if($hit){ $c.artist=$hit.artist; $c.artistSource="reprint of $($Matches[1]) $($Matches[2]) (via product slug)"; $urlref++ }
  }
}
# pass 4: "Additionals" sets (x-prefixed) mirror the base set
$addl=0
foreach($c in $cards){
  if($c.artist){continue}
  if($c.setCode -match '^x(.+)$'){
    $baseCode=$Matches[1]
    $hit=Lookup $baseCode $c.number
    if(-not $hit){ $sib=$byUrlNum["$baseCode|$(NN $c.number)"]; if($sib -and $sib.artist){ $c.artist=$sib.artist; $c.artistSource="same card as $baseCode $($c.number) (Additionals printing)"; $addl++; continue } }
    if($hit){ $c.artist=$hit.artist; $c.artistSource="same card as $baseCode $($c.number) (Additionals printing)"; $addl++ }
  }
}
$cards | ConvertTo-Json -Depth 5 | Set-Content "$base\_cards_stage2.json" -Encoding utf8NoBOM
$known=($cards|?{$_.artist}).Count
Write-Host "direct=$direct reprint-number=$rep reprint-slug=$urlref additionals=$addl"
Write-Host "artist known: $known / $($cards.Count)"
