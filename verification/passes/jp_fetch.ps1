$ErrorActionPreference='Continue'
$V=Split-Path -Parent $PSScriptRoot
$J="$V\cache\jp"
New-Item -ItemType Directory -Force -Path $J | Out-Null
$ua="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"
$hj=@{"Accept"="application/json,*/*";"X-Requested-With"="XMLHttpRequest";"Referer"="https://www.pokemon-card.com/card-search/"}
$hh=@{"Accept"="text/html,*/*"}

# 1) enumerate via official search API (all regulations)
$listFile="$J\cardids.json"
if(Test-Path $listFile){
  $ids=Get-Content $listFile -Raw -Encoding utf8|ConvertFrom-Json
  Write-Host "reusing cached id list: $($ids.Count)"
} else {
  $ids=@()
  foreach($kw in @([uri]::EscapeDataString("カビゴン"))){
    for($p=1;$p -le 6;$p++){
      # NOTE: 'pg' is NOT the page parameter (pg=1 returns 0 hits). The real one is 'page'.
      $u="https://www.pokemon-card.com/card-search/resultAPI.php?keyword=$kw&se_ta=&regulation_sidebar_form=all&pg=&illust=&sm_and_keyword=true&page=$p"
      try{ $r=Invoke-RestMethod -Uri $u -UserAgent $ua -Headers $hj -TimeoutSec 40 -ErrorAction Stop }catch{ break }
      if(-not $r.cardList){ break }
      foreach($c in $r.cardList){
        $setCode = if($c.cardThumbFile -match 'card_images/large/([A-Za-z0-9\.\-]+)/'){ $Matches[1] } else { $null }
        $ids += [pscustomobject]@{cardID=$c.cardID; name=$c.cardNameViewText; setCode=$setCode}
      }
      if($p -ge $r.maxPage){ break }
      Start-Sleep -Milliseconds 800
    }
  }
  $ids = $ids | Sort-Object cardID -Unique
  $ids | ConvertTo-Json -Depth 3 | Set-Content $listFile -Encoding utf8
  Write-Host "enumerated cardIDs: $($ids.Count)"
}

# 2) detail page per card (cached)
$n=0
foreach($c in $ids){
  $f="$J\card_$($c.cardID).json"
  if(Test-Path $f){ $n++; continue }
  $url="https://www.pokemon-card.com/card-search/details.php/card/$($c.cardID)/regu/all"
  try{ $r=Invoke-WebRequest -Uri $url -UserAgent $ua -Headers $hh -TimeoutSec 40 -ErrorAction Stop }catch{ continue }
  $html=$r.Content
  $txt=($html -replace '(?s)<script.*?</script>','' -replace '<[^>]+>',' ' -replace '&nbsp;',' ' -replace '\s+',' ')
  $num=$null; $tot=$null
  if($txt -match '(\d{1,3})\s*/\s*(\d{1,3})'){ $num=$Matches[1]; $tot=$Matches[2] }
  $setCode = if($html -match 'card_images/large/([A-Za-z0-9\.\-]+)/'){ $Matches[1] } else { $c.setCode }
  $ill = if($txt -match 'イラストレーター\s+([^\s]+(?:\s+[^\s]+){0,3}?)\s+(?:たね|HP|ポケモン|タイプ|ワザ|進化)'){ $Matches[1].Trim() } else { $null }
  [pscustomobject]@{cardID=$c.cardID;name=$c.name;setCode=$setCode;number=$num;setTotal=$tot;illustrator=$ill;url=$url} |
    ConvertTo-Json | Set-Content $f -Encoding utf8
  $n++
  Start-Sleep -Milliseconds 700
}
Write-Host "detail pages cached: $n"
