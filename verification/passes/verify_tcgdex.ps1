$ErrorActionPreference='Stop'
$V="C:\Users\marku\Claude\snorlax-cardmarket\verification"
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json

$LANG=@{'English'='en';'French'='fr';'German'='de';'Spanish'='es';'Italian'='it';'Portuguese'='pt';
 'Dutch'='nl';'Polish'='pl';'Russian'='ru';'Japanese'='ja';'Korean'='ko';'T-Chinese'='zh-tw';
 'S-Chinese'='zh-cn';'Indonesian'='id';'Thai'='th'}

$SET=@{'JU'='base2';'B2'='base4';'WP'='basep';'BCR'='bw7';'PLS'='bw8';'CL'='col1';'DP'='dp1';'SK'='ecard3';
 'DF'='ex15';'FL'='ex6';'TRR'='ex7';'GEN'='g1';'GH'='gym1';'LC'='lc';'POR'='me03';'RR'='pl2';'UNB'='sm10';
 'HIF'='sm115';'TEU'='sm9';'SM'='smp';'MEW'='sv03.5';'PAR'='sv04';'PAF'='sv04.5';'TWM'='sv06';'SSP'='sv08';
 'PRE'='sv08.5';'JTG'='sv09';'SVP'='svp';'SSH'='swsh1';'PGO'='swsh10.5';'LOR'='swsh11';'CRZ'='swsh12.5';
 'RCL'='swsh2';'VIV'='swsh4';'CRE'='swsh6';'FST'='swsh8';'SWSH'='swshp';'KSS'='xy0';'FCO'='xy10';
 'FLF'='xy2';'BKT'='xy8';'XYPR'='xyp';'sv2a'='SV2a';'sv5a'='SV5a';'sv4a'='SV4a';'m2a'='M2a';'m3'='M3';
 'mC'='MC';'PCG1'='PCG1';'PCG3'='PCG3';'PCG9'='PCG9';'svLN'='SVLN';'sv9'='SV9';'sm10'='SM10'}

function Norm($n){ if($null -eq $n){return ''}; $s="$n".Trim()
  if($s -match '^[A-Za-z\-]*?(\d+)$'){ return [string][int]$Matches[1] }
  return $s.ToUpper() }

# load caches
$byLang=@{}
foreach($l in ($LANG.Values|Select-Object -Unique)){
  $f="$V\cache\tcgdex_$l.json"
  if(Test-Path $f){ $d=Get-Content $f -Raw -Encoding utf8|ConvertFrom-Json; if($null -eq $d){$d=@()}; $byLang[$l]=@($d) } else { $byLang[$l]=@() }
}
# also fold pt-br into pt pool
if(Test-Path "$V\cache\tcgdex_pt-br.json"){ $byLang['pt'] = @($byLang['pt']) + @(Get-Content "$V\cache\tcgdex_pt-br.json" -Raw -Encoding utf8|ConvertFrom-Json) }

$hit=0;$miss=0
$evidence=@()
foreach($u in $units){
  if($u.status -eq 'confirmed'){ continue }
  $lg=$LANG[$u.language]
  if(-not $lg){ $u.status='no-source-available'; continue }
  $pool=$byLang[$lg]
  if(-not $pool -or $pool.Count -eq 0){ $u.status='pending'; $miss++; continue }
  $tset = $SET[$u.setCode]
  $cands = @($pool | Where-Object {
      $i=$_.id; $sid=$i.Substring(0,$i.LastIndexOf('-'))
      ((Norm $_.localId) -eq (Norm $u.number)) -and
      ( ($tset -and $sid -ieq $tset) -or ($sid -ieq $u.setCode) )
  })
  if($cands.Count -ge 1){
    $c=$cands[0]
    $u.status='confirmed'
    $u.sourceType='TCGdex API (open card database)'
    $u.sourceUrl="https://api.tcgdex.net/v2/$lg/cards/$($c.id)"
    $u.evidence="$lg card '$($c.name)' id=$($c.id) localId=$($c.localId)"
    $u.checkedAt=(Get-Date -Format s)
    $evidence += [pscustomobject]@{unitId=$u.unitId;lang=$u.language;source=$u.sourceUrl;name=$c.name;at=$u.checkedAt}
    $hit++
  } else { $miss++ }
}
$units | ConvertTo-Json -Depth 4 | Set-Content "$V\units.json" -Encoding utf8
if($evidence){ $evidence | ForEach-Object{ $_|ConvertTo-Json -Compress } | Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='tcgdex';completedAt=(Get-Date -Format s);confirmed=$hit} | ConvertTo-Json | Set-Content "$V\state.json" -Encoding utf8
Write-Host "confirmed this pass: $hit ; still unconfirmed: $miss"
Write-Host ""
$units | Group-Object status | Format-Table Count,Name -Auto
Write-Host "--- unconfirmed by language ---"
$units | Where-Object{$_.status -ne 'confirmed'} | Group-Object language | Sort-Object Count -Desc | Format-Table Count,Name -Auto
