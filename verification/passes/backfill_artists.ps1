$ErrorActionPreference='Stop'
$B="C:\redacted\Claude\snorlax-cardmarket"
$V="$B\verification"
$j=Get-Content "$B\snorlax_cards.json" -Raw -Encoding utf8|ConvertFrom-Json
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json

# official JP illustrator per (setCode|number|variant), harvested from pokemon-card.com
$art=@{}
foreach($u in $units){
  if($u.artist -and $u.sourceType -match 'Official Pokemon Japan'){
    $art["$($u.setCode)|$($u.number)|$($u.variant)"]=@($u.artist,$u.sourceUrl)
  }
}
$n=0
foreach($c in $j.cards){
  if($c.artist){ continue }
  $k="$($c.setCode)|$($c.number)|$(if($c.variantToken){$c.variantToken}else{'base'})"
  if($art.ContainsKey($k)){
    $c.artist=$art[$k][0]
    $c | Add-Member artistSource "Official Pokemon Japan card database (pokemon-card.com)" -Force
    $c | Add-Member artistSourceUrl $art[$k][1] -Force
    $n++
  }
}
$j | ConvertTo-Json -Depth 6 | Set-Content "$B\snorlax_cards.json" -Encoding utf8
Write-Host "artists backfilled into main dataset: $n"
Write-Host ("artist coverage now: {0} / {1}" -f (@($j.cards|?{$_.artist}).Count),$j.cards.Count)
