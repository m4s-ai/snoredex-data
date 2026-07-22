$ErrorActionPreference='Stop'
$B="C:\Users\marku\Claude\snorlax-cardmarket"
$V="$B\verification"
$fail=@()
function Check($name,$ok,$detail){
  $mark = if($ok){'OK  '}else{'FAIL'}
  Write-Host ("[{0}] {1}{2}" -f $mark,$name,$(if($detail){" - $detail"}else{""}))
  if(-not $ok){ $script:fail += $name }
}

$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json
$cards=(Get-Content "$B\snorlax_cards.json" -Raw -Encoding utf8|ConvertFrom-Json).cards
$excluded=Get-Content "$V\excluded_codecards.json" -Raw -Encoding utf8|ConvertFrom-Json

# --- 1. unit totals and identity ---
Check "719 units total" ($units.Count -eq 719) "found $($units.Count)"
$dupIds=@($units|Group-Object unitId|?{$_.Count -gt 1})
Check "unitIds unique" ($dupIds.Count -eq 0) "$($dupIds.Count) duplicates"
$statuses=$units|Group-Object status
$sMap=@{}; foreach($g in $statuses){$sMap[$g.Name]=$g.Count}
Check "no stray statuses" (@($statuses|?{$_.Name -notin @('confirmed','contradicted','needs-manual-review','pending')}).Count -eq 0) (($statuses|ForEach-Object{"$($_.Name)=$($_.Count)"}) -join ', ')
Check "status sum = 719" (($sMap.Values|Measure-Object -Sum).Sum -eq 719)

# --- 2. resolved units carry full evidence ---
$badEv=@(); $badSrc=@()
foreach($u in $units){
  if($u.status -in @('confirmed','contradicted')){
    if(-not ($u.evidence -is [string]) -or $u.evidence.Length -lt 20){ $badEv += $u.unitId }
    if([string]::IsNullOrWhiteSpace($u.sourceType)){ $badSrc += $u.unitId }
  }
}
Check "resolved units have evidence" ($badEv.Count -eq 0) (($badEv|Select-Object -First 5) -join ',')
Check "resolved units have sourceType" ($badSrc.Count -eq 0) (($badSrc|Select-Object -First 5) -join ',')

# --- 3. no stale manualReason on resolved units ---
$staleReason=@($units|?{$_.status -in @('confirmed','contradicted') -and $_.PSObject.Properties.Name -contains 'manualReason' -and $_.manualReason})
Check "no manualReason on resolved units" ($staleReason.Count -eq 0) (($staleReason|Select-Object -First 5 -Expand unitId) -join ',')

# --- 4. units cover exactly the non-code cards' languages ---
$expected=0
foreach($c in $cards){ if(-not $c.isCodeCard){ $expected += $c.languages.Count } }
Check "units (719) + excluded (75) match card langs" (($expected) -eq ($units.Count)) "non-code card langs=$expected"
Check "excluded code-card units = 75" ($excluded.Count -eq 75) "found $($excluded.Count)"

# --- 5. every unit maps to a card ---
$cardKeySet=@{}
foreach($c in $cards){ $vt = if($c.variantToken){$c.variantToken}else{'base'}; $cardKeySet["$($c.setCode)|$($c.number)|$vt"]=$true }
$orphan=@($units|?{ -not $cardKeySet.ContainsKey("$($_.setCode)|$($_.number)|$($_.variant)") })
Check "no orphaned units" ($orphan.Count -eq 0) (($orphan|Select-Object -First 5|%{"$($_.setCode) $($_.number) $($_.variant)"}) -join '; ')

# --- 6. images exist ---
$noImg=@($cards|?{ -not (Test-Path (Join-Path $B ($_.imageFile -replace '/','\'))) })
Check "all 198 images on disk" ($noImg.Count -eq 0) "$($noImg.Count) missing"

# --- 7. named variants present ---
$named=@($cards|?{$_.PSObject.Properties.Name -contains 'variantName' -and $_.variantName})
Check "named variants >= 11" ($named.Count -ge 11) "found $($named.Count)"

# --- 8. artist coverage ---
$artists=@($cards|?{$_.artist}).Count
Check "artist coverage 115/198" ($artists -eq 115) "found $artists"

# --- 9. evidence log is valid JSONL ---
$badLines=0; $lineNo=0
foreach($line in (Get-Content "$V\evidence.jsonl" -Encoding utf8)){
  $lineNo++
  if([string]::IsNullOrWhiteSpace($line)){continue}
  try{ $null=$line|ConvertFrom-Json }catch{ $badLines++ }
}
Check "evidence.jsonl parses ($lineNo lines)" ($badLines -eq 0) "$badLines bad lines"

# --- 10. remaining work is exactly as documented ---
$pend=@($units|?{$_.status -eq 'pending'})
$manual=@($units|?{$_.status -eq 'needs-manual-review'})
Check "9 pending" ($pend.Count -eq 9) (($pend|%{"$($_.setCode) $($_.number) $($_.language)"}) -join '; ')
Check "5 manual review, all Portuguese" (($manual.Count -eq 5) -and (@($manual|?{$_.language -ne 'Portuguese'}).Count -eq 0)) (($manual|%{"$($_.setCode) $($_.variant)"}) -join '; ')

Write-Host ""
if($fail.Count){ Write-Host "=== REVIEW FAILED: $($fail -join ', ') ===" } else { Write-Host "=== ALL CHECKS PASSED ===" }
