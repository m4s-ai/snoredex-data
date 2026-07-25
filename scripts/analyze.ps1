$ErrorActionPreference='Stop'
$base=Split-Path -Parent $PSScriptRoot
$stage = if(Test-Path "$base\_cards_stage3.json"){"$base\_cards_stage3.json"}else{"$base\_cards_stage2.json"}
$cards=Get-Content $stage -Raw -Encoding utf8|ConvertFrom-Json

$WEST=@('English','French','German','Spanish','Italian','Portuguese')
$ASIA=@('Japanese','Korean','T-Chinese')

function Market($langs){
  if($langs -contains 'English'){ if($langs.Count -ge 10){return 'Global (code card)'}; return 'Western' }
  if($langs -contains 'Japanese'){ return 'Japanese' }
  if(($langs -contains 'S-Chinese') -and $langs.Count -eq 1){ return 'Simplified Chinese' }
  if(($langs -contains 'Indonesian') -or ($langs -contains 'Thai')){ return 'SEA promo' }
  if($langs -contains 'T-Chinese'){ return 'Traditional Chinese' }
  return 'Other'
}
foreach($c in $cards){ $c | Add-Member market (Market $c.languages) -Force }

# ---- Language drift ----
$drift=@()
foreach($c in $cards){
  $L=$c.languages
  if($c.market -eq 'Western'){
    $missing = @($WEST | Where-Object { $_ -notin $L })
    $extra   = @($L | Where-Object { $_ -notin $WEST })
    if($missing.Count -or $extra.Count){
      $drift += [pscustomobject]@{ card="$($c.name) ($($c.setCode) $($c.number))"; setName=$c.setName; market=$c.market;
        languages=($L -join ', '); missingVsWesternBaseline=($missing -join ', '); extraVsWesternBaseline=($extra -join ', ') }
    }
  } elseif($c.market -eq 'Japanese'){
    $missing = @($ASIA | Where-Object { $_ -notin $L })
    $extra   = @($L | Where-Object { $_ -notin $ASIA })
    if($missing.Count -or $extra.Count){
      $drift += [pscustomobject]@{ card="$($c.name) ($($c.setCode) $($c.number))"; setName=$c.setName; market=$c.market;
        languages=($L -join ', '); missingVsWesternBaseline=($missing -join ', '); extraVsWesternBaseline=($extra -join ', ') }
    }
  }
}
$drift | ConvertTo-Json -Depth 4 | Set-Content "$base\analysis_language_drift.json" -Encoding utf8NoBOM

# ---- Same card across releases (Cardmarket cardKey = name + attack names) ----
$groups = $cards | Where-Object {$_.cardKey} | Group-Object cardKey | Where-Object {$_.Count -gt 1} | Sort-Object Count -Descending
$shared = foreach($g in $groups){
  $arts = @($g.Group | Where-Object {$_.artist} | Select-Object -Expand artist -Unique)
  [pscustomobject]@{
    cardKey=$g.Name
    printings=$g.Count
    distinctSets=@($g.Group|Select-Object -Expand setName -Unique).Count
    markets=(@($g.Group|Select-Object -Expand market -Unique|Sort-Object) -join ', ')
    knownArtists=(@($arts) -join ', ')
    artistCount=@($arts).Count
    rarities=(@($g.Group|Select-Object -Expand rarity -Unique|Sort-Object) -join ', ')
    releases=@($g.Group | ForEach-Object{ [pscustomobject]@{ set=$_.setName; code="$($_.setCode) $($_.number)"; rarity=$_.rarity; variant=$_.variantToken; artist=$_.artist; market=$_.market; image=$_.imageFile } })
  }
}
$shared | ConvertTo-Json -Depth 6 | Set-Content "$base\analysis_shared_cards.json" -Encoding utf8NoBOM

# ---- Artists ----
$byArtist = $cards | Where-Object {$_.artist} | Group-Object artist | Sort-Object Count -Descending | ForEach-Object{
  [pscustomobject]@{ artist=$_.Name; printings=$_.Count
    cards=@($_.Group | ForEach-Object{ "$($_.name) ($($_.setCode) $($_.number)) [$($_.setName)]" }) }
}
$byArtist | ConvertTo-Json -Depth 4 | Set-Content "$base\analysis_artists.json" -Encoding utf8NoBOM

# ---- Variants: same set+number, multiple products ----
$var = $cards | Group-Object {"$($_.setCode)|$($_.number)"} | Where-Object {$_.Count -gt 1} | ForEach-Object{
  [pscustomobject]@{ setAndNumber=$_.Name; count=$_.Count
    products=@($_.Group|ForEach-Object{ [pscustomobject]@{ variant=$_.variantToken; rarity=$_.rarity; name=$_.name; url=$_.productUrl; image=$_.imageFile } }) }
}
$var | ConvertTo-Json -Depth 5 | Set-Content "$base\analysis_variants.json" -Encoding utf8NoBOM

Write-Host "drift rows      : $($drift.Count)"
Write-Host "shared groups   : $(@($shared).Count)"
Write-Host "artists         : $(@($byArtist).Count)"
Write-Host "variant clusters: $(@($var).Count)"
Write-Host ""
Write-Host "--- market mix ---"
$cards | Group-Object market | Sort-Object Count -Desc | Select-Object Count,Name | Format-Table -Auto
