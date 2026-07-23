$ErrorActionPreference='Stop'
$B=Split-Path -Parent $PSScriptRoot
$V="$B\verification"
$fail=@()
function Check($name,$ok,$detail){
  $mark = if($ok){'OK  '}else{'FAIL'}
  Write-Host ("[{0}] {1}{2}" -f $mark,$name,$(if($detail){" - $detail"}else{""}))
  if(-not $ok){ $script:fail += $name }
}

$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json
$cardDoc=Get-Content "$B\snorlax_cards.json" -Raw -Encoding utf8|ConvertFrom-Json
$cards=$cardDoc.cards
$excluded=Get-Content "$V\excluded_codecards.json" -Raw -Encoding utf8|ConvertFrom-Json
$finishDoc=Get-Content "$V\finish_units.json" -Raw -Encoding utf8|ConvertFrom-Json
$finishUnits=$finishDoc.units
$finishReview=Get-Content "$V\FINISH_REVIEW.json" -Raw -Encoding utf8|ConvertFrom-Json

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

# --- 11. finish-verification layer ---
Check "637 finish units" ($finishUnits.Count -eq 637) "found $($finishUnits.Count)"
$finishDupIds=@($finishUnits|Group-Object finishUnitId|?{$_.Count -gt 1})
Check "finishUnitIds unique" ($finishDupIds.Count -eq 0) "$($finishDupIds.Count) duplicates"
$claimFinishKeys=@($units|%{"$($_.setCode)|$($_.number)|$($_.language)"}|Sort-Object -Unique)
$actualFinishKeys=@($finishUnits|%{"$($_.setCode)|$($_.number)|$($_.language)"}|Sort-Object -Unique)
$finishKeyDiff=@(Compare-Object $claimFinishKeys $actualFinishKeys)
Check "finish units exactly cover claim groups" (($actualFinishKeys.Count -eq 637) -and ($finishKeyDiff.Count -eq 0)) "$($finishKeyDiff.Count) key differences"

$allowedFinishes=@('non-holo','holo','reverse-holo','mirror-holo','unknown')
$allowedAvailabilityStatuses=@('confirmed','owner-attested','marketplace-claimed','pending','not-applicable')
$allowedPrintingStatuses=@('confirmed','owner-attested','marketplace-claimed','pending')
$allowedMapStatuses=@('confirmed','partial','pending','not-applicable')
$allowedPatternStatuses=@('confirmed','partial','pending','not-applicable')
$allowedCompletenessStatuses=@('complete-manifest','positive-evidence-only','pending','not-applicable')
$badFinishState=@($finishUnits|?{
  $_.applicabilityStatus -notin @('applicable','not-applicable') -or
  $_.availabilityStatus -notin $allowedAvailabilityStatuses -or
  $_.productMappingStatus -notin $allowedMapStatuses -or
  $_.patternStatus -notin $allowedPatternStatuses -or
  $_.completenessStatus -notin $allowedCompletenessStatuses -or
  @($_.printings|?{$_.finish -notin $allowedFinishes -or $_.verificationStatus -notin $allowedPrintingStatuses}).Count -or
  ($_.applicabilityStatus -eq 'not-applicable' -and (
    $_.availabilityStatus -ne 'not-applicable' -or @($_.printings).Count -ne 0 -or @($_.unresolved).Count -ne 0 -or
    @($_.products|?{$_.claimStatus -ne 'contradicted'}).Count -ne 0
  ))
})
$notApplicableFinish=@($finishUnits|?{$_.applicabilityStatus -eq 'not-applicable'})
$reviewNotApplicable=@($finishReview.units|?{$_.availabilityStatus -eq 'not-applicable'})
$finishStateOk=(
  $badFinishState.Count -eq 0 -and $notApplicableFinish.Count -eq 64 -and
  @($finishUnits|?{$_.completenessStatus -eq 'complete-manifest'}).Count -eq 4 -and
  $finishReview.meta.count -eq 233 -and @($finishReview.units).Count -eq 233 -and
  $reviewNotApplicable.Count -eq 0
)
Check "finish taxonomy, applicability, and review queue valid" $finishStateOk "bad=$($badFinishState.Count), not-applicable=$($notApplicableFinish.Count), review=$($finishReview.meta.count)"

$allPrintingIds=@($finishUnits|%{$_.printings}|Select-Object -Expand printingId)
$dupPrintingIds=@($allPrintingIds|Group-Object|?{$_.Count -gt 1})
Check "printingIds unique" (($allPrintingIds.Count -gt 0) -and ($dupPrintingIds.Count -eq 0)) "$($dupPrintingIds.Count) duplicates"

$badFinishSources=@()
$badFinishMappings=@()
$badMarkingRoles=@()
foreach($finishUnit in $finishUnits){
  $productVariants=@($finishUnit.products|Select-Object -Expand variant -Unique)
  foreach($printing in $finishUnit.printings){
    if(@($printing.sources).Count -eq 0){ $badFinishSources += $printing.printingId }
    foreach($source in @($printing.sources)){
      if($source.supportsAbsence -eq $true -and ($source.authorityTier -ne 'official-primary' -or $source.coverage -ne 'complete-manifest')){
        $badFinishSources += $printing.printingId
      }
    }
    foreach($mappedVariant in @($printing.mappedVariants)){
      if($mappedVariant -notin $productVariants){ $badFinishMappings += $printing.printingId }
    }
    foreach($marking in @($printing.markings|Where-Object {$_})){
      if($marking.role -notin @('reverse-holo-treatment','distribution-promo')){ $badMarkingRoles += $printing.printingId }
      if($marking.role -eq 'reverse-holo-treatment' -and $printing.finish -ne 'reverse-holo'){ $badMarkingRoles += $printing.printingId }
    }
  }
}
Check "finish printings have sources" ($badFinishSources.Count -eq 0) (($badFinishSources|Select-Object -First 5) -join ',')
Check "finish mappings reference local products" ($badFinishMappings.Count -eq 0) (($badFinishMappings|Select-Object -First 5) -join ',')
Check "stamp roles valid and finish-safe" ($badMarkingRoles.Count -eq 0) (($badMarkingRoles|Select-Object -First 5) -join ',')

$dragonFrontiers=@($finishUnits|?{$_.setCode -eq 'DF' -and $_.number -eq '10'}|%{$_.printings}|?{
  $_.finish -eq 'reverse-holo' -and $_.foilPattern -eq 'plain-foil-on-pokemon' -and
  @($_.markings|?{$_.kind -eq 'set-logo' -and $_.role -eq 'reverse-holo-treatment'}).Count -eq 1
})
$battleAcademy=$finishUnits|?{$_.setCode -eq 'BA20' -and $_.number -eq 'MWT' -and $_.language -eq 'English'}
$classic=$finishUnits|?{$_.setCode -eq 'CLV' -and $_.number -eq '016' -and $_.language -eq 'English'}
$prize3=$finishUnits|?{$_.setCode -eq 'PPS3 LOR' -and $_.number -eq 'LOR 143' -and $_.language -eq 'English'}
$prize7=$finishUnits|?{$_.setCode -eq 'PPS7 JTG' -and $_.number -eq 'JTG 117' -and $_.language -eq 'English'}
$jtgPromos=$finishUnits|?{$_.setCode -eq 'xJTG' -and $_.number -eq '117' -and $_.language -eq 'English'}
$prismatic=$finishUnits|?{$_.setCode -eq 'xPRE' -and $_.number -eq '076' -and $_.language -eq 'English'}
$specialFinishOk=(
  $dragonFrontiers.Count -eq 4 -and
  @($battleAcademy.printings|?{$_.finish -eq 'non-holo'}).Count -eq 1 -and
  @($classic.printings|?{$_.finish -eq 'holo'}).Count -eq 1 -and
  @($prize3.printings|?{$_.finish -eq 'non-holo'}).Count -eq 1 -and
  @($prize7.printings|?{$_.finish -eq 'non-holo'}).Count -eq 1 -and
  @($jtgPromos.printings|?{$_.finish -eq 'holo' -and $_.foilPattern -eq 'cosmos'}).Count -eq 3 -and
  @($prismatic.printings|?{$_.finish -eq 'holo' -and $_.cardSize -eq 'standard'}).Count -eq 1 -and
  @($prismatic.printings|?{$_.finish -eq 'holo' -and $_.cardSize -eq 'jumbo'}).Count -eq 1
)
Check "special finish cases modeled" $specialFinishOk "DF=$($dragonFrontiers.Count), xJTG=$(@($jtgPromos.printings).Count), xPRE=$(@($prismatic.printings).Count)"

$hopEnglish=$finishUnits|?{$_.setCode -eq 'JTG' -and $_.number -eq '117' -and $_.language -eq 'English'}
$hopEnglishFinishes=@($hopEnglish.availableFinishes)
$hopEnglishOk=$hopEnglishFinishes.Count -eq 2 -and @('holo','reverse-holo'|?{$_ -notin $hopEnglishFinishes}).Count -eq 0
Check "regular JTG 117 discloses holo + reverse only" $hopEnglishOk ($hopEnglishFinishes -join ',')

$badCardFinishSummary=@($cards|?{
  if($_.isCodeCard){ $_.finishAvailability.status -ne 'not-applicable' }
  else { -not $_.finishAvailability -or @($_.finishAvailability.byLanguage).Count -ne @($_.languages).Count }
})
Check "all cards carry finish summaries" ($badCardFinishSummary.Count -eq 0) (($badCardFinishSummary|Select-Object -First 5|%{"$($_.setCode) $($_.number)"}) -join '; ')

Write-Host ""
if($fail.Count){ Write-Host "=== REVIEW FAILED: $($fail -join ', ') ===" } else { Write-Host "=== ALL CHECKS PASSED ===" }
