$ErrorActionPreference='Stop'
$base="C:\Users\marku\Claude\snorlax-cardmarket"
$rows=@()
foreach($f in 1..3){ $rows += (Get-Content "$base\_chunk$f.json" -Raw -Encoding utf8 | ConvertFrom-Json) }
Write-Host "rows: $($rows.Count)"

$IMG="https://product-images.s3.cardmarket.com/"
$CM="https://www.cardmarket.com/en/Pokemon/Products/Singles/"

$cards = foreach($r in $rows){
  $axes = @($r[9] -split ',' | Where-Object {$_}) 
  [pscustomobject]@{
    name          = $r[0]
    setCode       = $r[1]
    number        = $r[2]
    setName       = $r[3]
    rarity        = ($r[4] -replace '\s+$','')
    languages     = @($r[5] -split ',' | Where-Object {$_})
    languageCount = @($r[5] -split ',' | Where-Object {$_}).Count
    imageUrl      = $IMG + $r[6]
    imageFile     = $null
    productUrl    = $CM + $r[7]
    variantToken  = $(if($r[8]){$r[8]}else{$null})
    variantAxes   = $axes
    hasReverseHolo= [bool]($axes -contains 'Reverse Holo')
    hasFirstEdition=[bool]($axes -contains 'First Edition?')
    cardKey       = $(if($r[10]){$r[10]}else{$null})
    versionsCount = $(if($r[11] -is [int]){$r[11]}else{$null})
    availableItems= [int]$r[12]
    artist        = $null
    artistSource  = $null
  }
}
$cards | ConvertTo-Json -Depth 5 | Set-Content "$base\_cards_stage1.json" -Encoding utf8
Write-Host "cards: $($cards.Count)  langs-empty: $(($cards|?{$_.languageCount -eq 0}).Count)"
