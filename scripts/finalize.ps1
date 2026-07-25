$ErrorActionPreference='Stop'
$base=Split-Path -Parent $PSScriptRoot
$cards=Get-Content "$base\_cards_stage3.json" -Raw -Encoding utf8|ConvertFrom-Json
$WEST=@('English','French','German','Spanish','Italian','Portuguese')
$ASIA=@('Japanese','Korean','T-Chinese')
function Market($L){
  if($L -contains 'English'){ if($L.Count -ge 10){return 'Global (code card)'}; return 'Western' }
  if($L -contains 'Japanese'){ return 'Japanese' }
  if(($L -contains 'S-Chinese') -and $L.Count -eq 1){ return 'Simplified Chinese' }
  if(($L -contains 'Indonesian') -or ($L -contains 'Thai')){ return 'SEA promo' }
  if($L -contains 'T-Chinese'){ return 'Traditional Chinese' }
  return 'Other' }
foreach($c in $cards){
  $m=Market $c.languages
  $baseline = if($m -eq 'Western'){$WEST}elseif($m -eq 'Japanese'){$ASIA}else{@()}
  $c | Add-Member market $m -Force
  $c | Add-Member languagesMissingVsMarketBaseline (@($baseline|?{$_ -notin $c.languages})) -Force
  $c | Add-Member languagesBeyondMarketBaseline (@($c.languages|?{$baseline.Count -and $_ -notin $baseline})) -Force
  $c | Add-Member isCodeCard ([bool]($c.name -match 'Code Card')) -Force
}
$out=[pscustomobject]@{
  meta=[pscustomobject]@{
    source='https://www.cardmarket.com/en/Pokemon/Products/Search?category=-1&searchString=snorlax&searchMode=v2'
    retrieved=(Get-Date -Format 'yyyy-MM-dd')
    totalProductsOnCardmarket=242
    singlesCaptured=$cards.Count
    nonCardProductsExcluded=44
    artistSources=@('pokemontcg.io v2 API','limitlesstcg.com (3 cards missing upstream)')
    notes=@(
      'languages = languages Cardmarket actually lists offers in for that product; it is marketplace availability, not an official print-run manifest.'
      'cardKey = Cardmarket Versions grouping (card name + attack names). Same cardKey = same card text, NOT necessarily same artwork.'
      'variantToken = Cardmarket -V1/-V2/-V3 slug, used to separate distinct printings sharing a collector number.'
      'variantAxes = filters Cardmarket exposes for the product (Reverse Holo / First Edition indicate those variants exist).'
      'artist is only available for English-market releases; Japanese/Simplified-Chinese printings are not covered by the artist sources.'
    )
  }
  cards=$cards
}
$out | ConvertTo-Json -Depth 6 | Set-Content "$base\snorlax_cards.json" -Encoding utf8NoBOM
Write-Host "wrote snorlax_cards.json  cards=$($cards.Count)  withArtist=$(($cards|?{$_.artist}).Count)  withImage=$(($cards|?{$_.imageFile}).Count)"
