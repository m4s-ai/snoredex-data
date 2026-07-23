$ErrorActionPreference='Stop'
$base=Split-Path -Parent $PSScriptRoot
$j=Get-Content "$base\snorlax_cards.json" -Raw -Encoding utf8|ConvertFrom-Json
$units=@()
$i=0
foreach($c in $j.cards){
  foreach($l in $c.languages){
    $units += [pscustomobject]@{
      unitId    = "U{0:D4}" -f $i
      cardName  = $c.name
      setCode   = $c.setCode
      setName   = $c.setName
      number    = $c.number
      variant   = $(if($c.variantToken){$c.variantToken}else{'base'})
      language  = $l
      market    = $c.market
      rarity    = $c.rarity
      cardKey   = $c.cardKey
      artist    = $c.artist
      cmUrl     = $c.productUrl
      image     = $c.imageFile
      status    = 'pending'
      sourceUrl = $null
      sourceType= $null
      evidence  = $null
      checkedAt = $null
    }
    $i++
  }
}
$units | ConvertTo-Json -Depth 4 | Set-Content "$base\verification\units.json" -Encoding utf8
Write-Host "units: $($units.Count)"
Write-Host "distinct sets: $(($units|Select-Object -Expand setName -Unique).Count)"
Write-Host "distinct set x language: $(($units|ForEach-Object{"$($_.setName)|$($_.language)"}|Select-Object -Unique).Count)"
Write-Host ""
$units|Group-Object language|Sort-Object Count -Desc|Select-Object Count,Name|Format-Table -Auto
