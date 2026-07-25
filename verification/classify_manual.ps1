$ErrorActionPreference='Stop'
$B=Split-Path -Parent $PSScriptRoot
$V="$B\verification"
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json

# Units that no card database can ever evidence, for structural reasons.
# They stay in the dataset but leave the "open" pool, so the open count reflects real remaining work.
function Reason($u){
  # -cmatch, NOT -match. PowerShell's -match is case-insensitive, so '^x' also caught
  # XY-P, XY2, XY10 and XYPR and parked 12 ordinary units in manual review, where every
  # later evidence pass then skipped them. See fix_misclassified.ps1.
  if($u.setCode -cmatch '^x')                     { return 'Cardmarket "Additionals" grouping - not a publisher product, absent from every card database' }
  if($u.setCode -cmatch '^PPS\d')                 { return 'Play! Pokemon Prize Pack - the card is documented, but no source records distribution languages' }
  return $null
}
$n=0
foreach($u in $units){
  if($u.status -in @('confirmed','contradicted')){ continue }
  $r=Reason $u
  if(-not $r){ continue }
  # English prize-pack units are already confirmed; only the undocumented languages land here
  $u.status='needs-manual-review'
  $u | Add-Member manualReason $r -Force
  $u.checkedAt=(Get-Date -Format s)
  $n++
}
$units|ConvertTo-Json -Depth 4|Set-Content "$V\units.json" -Encoding utf8NoBOM

$m=@($units|?{$_.status -eq 'needs-manual-review'})
# grouped, decision-ready export
$grp = $m | Group-Object {"$($_.cardName)|$($_.setCode) $($_.number)|$($_.variant)"} | ForEach-Object{
  $g=$_.Group[0]
  [pscustomobject]@{
    card="$($g.cardName) ($($g.setCode) $($g.number))"
    variant=$g.variant; setName=$g.setName; rarity=$g.rarity
    languagesToDecide=@($_.Group|Select-Object -Expand language|Sort-Object)
    alreadyConfirmed=@($units|?{$_.setCode -eq $g.setCode -and $_.number -eq $g.number -and $_.variant -eq $g.variant -and $_.status -eq 'confirmed'}|Select-Object -Expand language|Sort-Object)
    reason=$g.manualReason
    cardmarketUrl=$g.cmUrl
    image=$g.image
    verdict=''      # <- fill in: confirmed | false
    yourSource=''   # <- fill in
  }
} | Sort-Object card
$grp | ConvertTo-Json -Depth 5 | Set-Content "$V\MANUAL_REVIEW.json" -Encoding utf8NoBOM

# flat CSV for quick editing
$m | Select-Object unitId,cardName,setCode,number,variant,language,setName,rarity,cmUrl,manualReason,
  @{n='verdict';e={''}},@{n='yourSource';e={''}} |
  Export-Csv "$V\MANUAL_REVIEW.csv" -NoTypeInformation -Encoding utf8NoBOM

Write-Host "moved to manual review: $n units, $(@($grp).Count) card-variants"
$units|Group-Object status|Sort-Object Count -Desc|Format-Table Count,Name -Auto
$m|Group-Object manualReason|Format-Table Count,Name -Auto -Wrap
