$ErrorActionPreference='Stop'
$V=$PSScriptRoot
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json
$conf=@($units|?{$_.status -eq 'confirmed'})
$contra=@($units|?{$_.status -eq 'contradicted'})
$manual=@($units|?{$_.status -eq 'needs-manual-review'})
$open=@($units|?{$_.status -notin @('confirmed','contradicted','needs-manual-review')})

$conf | Select-Object unitId,cardName,setCode,setName,number,variant,language,sourceType,sourceUrl,evidence,checkedAt |
  ConvertTo-Json -Depth 4 | Set-Content "$V\confirmed_sources.json" -Encoding utf8NoBOM

# CONTRADICTED: Cardmarket claims the language, an external source says otherwise
$contra | Select-Object unitId,cardName,setCode,setName,number,variant,language,sourceType,sourceUrl,evidence,cmUrl |
  ConvertTo-Json -Depth 4 | Set-Content "$V\CONTRADICTED.json" -Encoding utf8NoBOM

# OPEN: still no external source either way
$grp = $open | Group-Object {"$($_.cardName)|$($_.setCode) $($_.number)|$($_.variant)"} | ForEach-Object{
  $g=$_.Group[0]
  [pscustomobject]@{
    card="$($g.cardName) ($($g.setCode) $($g.number))"; setName=$g.setName; variant=$g.variant
    market=$g.market; rarity=$g.rarity; cmUrl=$g.cmUrl; image=$g.image
    openLanguages=@($_.Group|Select-Object -Expand language|Sort-Object)
    confirmedLanguages=@($units|?{$_.setCode -eq $g.setCode -and $_.number -eq $g.number -and $_.variant -eq $g.variant -and $_.status -eq 'confirmed'}|Select-Object -Expand language|Sort-Object)
  }
} | Sort-Object {$_.openLanguages.Count} -Descending
$grp | ConvertTo-Json -Depth 5 | Set-Content "$V\UNCONFIRMED.json" -Encoding utf8NoBOM

$byCard=@($units|Group-Object {"$($_.setCode)|$($_.number)|$($_.variant)"})
$full=@($byCard|?{ @($_.Group|?{$_.status -notin @('confirmed','contradicted')}).Count -eq 0 })
$resolvable=$units.Count - $manual.Count

Write-Host "=== COVERAGE ==="
Write-Host ("total units          : {0}" -f $units.Count)
Write-Host ("confirmed            : {0}  ({1:N1}% of all, {2:N1}% of resolvable)" -f $conf.Count,(100*$conf.Count/$units.Count),(100*$conf.Count/$resolvable))
Write-Host ("contradicted         : {0}   <- Cardmarket claims it, external source says no" -f $contra.Count)
Write-Host ("needs manual review  : {0}   <- structurally undocumentable, see MANUAL_REVIEW.csv" -f $manual.Count)
Write-Host ("still open           : {0}" -f $open.Count)
Write-Host ("card-variants fully resolved: {0} / {1}" -f $full.Count,$byCard.Count)
Write-Host ""
Write-Host "=== CONTRADICTED (highlight) ==="
$contra | Select-Object @{n='card';e={"$($_.cardName) ($($_.setCode) $($_.number)) $($_.variant)"}},language,@{n='why';e={$_.evidence}} | Format-Table -Auto -Wrap
Write-Host "=== open units by language ==="
$open|Group-Object language|Sort-Object Count -Desc|Format-Table Count,Name -Auto
