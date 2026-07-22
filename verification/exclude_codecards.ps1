$ErrorActionPreference='Stop'
$V="C:\Users\marku\Claude\snorlax-cardmarket\verification"
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json

$isCode = { param($u) $u.cardName -match '(?i)code card' }
$code=@($units|Where-Object{ & $isCode $_ })
$keep=@($units|Where-Object{ -not (& $isCode $_) })

if($code.Count){
  $code | ConvertTo-Json -Depth 4 | Set-Content "$V\excluded_codecards.json" -Encoding utf8
}
$keep | ConvertTo-Json -Depth 4 | Set-Content "$V\units.json" -Encoding utf8

Write-Host "excluded code-card units : $($code.Count)"
Write-Host "excluded distinct products: $(@($code|Group-Object cmUrl).Count)"
Write-Host "remaining units          : $($keep.Count)"
Write-Host ""
$c=@($keep|Where-Object{$_.status -eq 'confirmed'})
Write-Host ("confirmed: {0} / {1}  ({2:N1}%)" -f $c.Count,$keep.Count,(100*$c.Count/$keep.Count))
Write-Host ""
$keep|Where-Object{$_.status -ne 'confirmed'}|Group-Object language|Sort-Object Count -Desc|Format-Table Count,Name -Auto
