$ErrorActionPreference='Continue'
$V="C:\Users\marku\Claude\snorlax-cardmarket\verification"
$A="$V\cache\asia"
New-Item -ItemType Directory -Force -Path $A | Out-Null
$ua="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"
$h=@{"Accept"="text/html,*/*"}

$queries=@(
 @{loc='tw';kw='卡比獸'},
 @{loc='th';kw='Snorlax'},
 @{loc='id';kw='Snorlax'},
 @{loc='sg';kw='Snorlax'}
)

$idFile="$A\ids.json"
if(Test-Path $idFile){
  $ids=@{}; (Get-Content $idFile -Raw -Encoding utf8|ConvertFrom-Json)|ForEach-Object{$ids[$_]=$true}
  Write-Host "reusing cached id list: $($ids.Count)"
} else {
  $ids=@{}
  foreach($q in $queries){
    for($p=1;$p -le 8;$p++){
      $u="https://asia.pokemon-card.com/$($q.loc)/card-search/list/?pageNo=$p&keyword=$([uri]::EscapeDataString($q.kw))"
      try{ $r=Invoke-WebRequest -Uri $u -UserAgent $ua -Headers $h -TimeoutSec 40 -ErrorAction Stop }catch{ break }
      $m=[regex]::Matches($r.Content,'/card-search/detail/(\d+)/')
      if($m.Count -eq 0){ break }
      foreach($x in $m){ $ids["$($q.loc)|$($x.Groups[1].Value)"]=$true }
      Start-Sleep -Milliseconds 700
    }
    Write-Host ("search {0,-3} -> total {1}" -f $q.loc,$ids.Count)
  }
  $ids.Keys | ConvertTo-Json | Set-Content $idFile -Encoding utf8
}

$n=0
foreach($k in @($ids.Keys)){
  $parts = $k -split '\|'
  $loc=$parts[0]; $id=$parts[1]
  $f="$A\${loc}_$id.json"
  if(Test-Path $f){ $n++; continue }
  try{ $r=Invoke-WebRequest -Uri "https://asia.pokemon-card.com/$loc/card-search/detail/$id/" -UserAgent $ua -Headers $h -TimeoutSec 40 -ErrorAction Stop }
  catch{ continue }
  $c=$r.Content
  $num = if($c -match 'collectorNumber">\s*([0-9A-Za-z]+)\s*/'){ $Matches[1] } else { $null }
  $exp = if($c -match 'expansionCodes=([A-Za-z0-9\.\-]+)'){ $Matches[1] } else { $null }
  $nm  = if($c -match '<h1[^>]*>\s*([^<]+?)\s*</h1>'){ $Matches[1] } else { $null }
  $ill = if($c -match '(?s)繪師|illustrator'){ if($c -match '(?s)(?:繪師|illustrator)[^>]*>[\s\S]{0,200}?>\s*([^<]{2,40}?)\s*<'){ $Matches[1] } else { $null } } else { $null }
  [pscustomobject]@{loc=$loc;id=$id;number=$num;expansion=$exp;name=$nm;illustrator=$ill;
    url="https://asia.pokemon-card.com/$loc/card-search/detail/$id/"} | ConvertTo-Json | Set-Content $f -Encoding utf8
  $n++
  Start-Sleep -Milliseconds 500
}
Write-Host "detail pages cached: $n"
