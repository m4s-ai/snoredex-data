$ErrorActionPreference='Continue'
$V=Split-Path -Parent $PSScriptRoot
$A="$V\cache\asia"
$ua="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"
$h=@{"Accept"="text/html,*/*"}
# NOTE: the Thai locale does not respond to "Snorlax"; the Thai name is required.
$kw='คาบิกอน'
$ids=@{}
for($p=1;$p -le 6;$p++){
  $u="https://asia.pokemon-card.com/th/card-search/list/?pageNo=$p&keyword=$([uri]::EscapeDataString($kw))"
  try{ $r=Invoke-WebRequest -Uri $u -UserAgent $ua -Headers $h -TimeoutSec 40 -ErrorAction Stop }catch{ break }
  $m=[regex]::Matches($r.Content,'/card-search/detail/(\d+)/')
  if($m.Count -eq 0){ break }
  foreach($x in $m){ $ids[$x.Groups[1].Value]=$true }
  Start-Sleep -Milliseconds 700
}
Write-Host "th detail ids: $($ids.Count)"
$n=0
foreach($id in @($ids.Keys)){
  $f="$A\th_$id.json"
  if(Test-Path $f){ $n++; continue }
  try{ $r=Invoke-WebRequest -Uri "https://asia.pokemon-card.com/th/card-search/detail/$id/" -UserAgent $ua -Headers $h -TimeoutSec 40 -ErrorAction Stop }catch{ continue }
  $c=$r.Content
  $num = if($c -match 'collectorNumber">\s*([0-9A-Za-z]+)\s*/'){ $Matches[1] } else { $null }
  $exp = if($c -match 'expansionCodes=([A-Za-z0-9\.\-]+)'){ $Matches[1] } else { $null }
  [pscustomobject]@{loc='th';id=$id;number=$num;expansion=$exp;name=$null;illustrator=$null;
    url="https://asia.pokemon-card.com/th/card-search/detail/$id/"} | ConvertTo-Json | Set-Content $f -Encoding utf8
  $n++
  Start-Sleep -Milliseconds 500
}
Write-Host "th detail pages cached: $n"
Get-ChildItem $A -Filter 'th_*.json' | ForEach-Object{Get-Content $_.FullName -Raw -Encoding utf8|ConvertFrom-Json} |
  Select-Object expansion,number | Sort-Object expansion,number | Format-Table -Auto
