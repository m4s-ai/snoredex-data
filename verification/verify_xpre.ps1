$ErrorActionPreference='Stop'
$V="C:\Users\marku\Claude\snorlax-cardmarket\verification"
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json

# xPRE 076 = Prismatic Evolutions: Additionals (Snorlax ex, "Prismatic Evolutions" stamp V1 /
# Jumbo V2). Owner (domain expert) confirms it exists in French, German, Italian and European
# Spanish. Portuguese and Latin-American Spanish are explicitly NOT confirmed. Cardmarket's
# "Spanish" is European Spanish, which is the confirmed one; LATAM Spanish is not a language
# tracked in this dataset. Portuguese stays in manual review.
$confirmLangs=@('French','German','Italian','Spanish')
$attest='Owner (domain expert) confirms Prismatic Evolutions: Additionals Snorlax ex (xPRE 076) exists in {0}. Confirmed languages: French, German, Italian and European Spanish. NOTE the owner explicitly does NOT confirm Portuguese or Latin-American Spanish; Cardmarket "Spanish" is European Spanish (the confirmed one). English was already documented from the Prismatic Evolutions set list.'

$applied=0; $logRows=@()
foreach($unit in $units){
  if($unit.setCode -ne 'xPRE'){ continue }
  if($unit.language -notin $confirmLangs){ continue }
  if($unit.status -eq 'confirmed'){ continue }
  $unit.status='confirmed'
  $unit.sourceUrl='(owner attestation, domain expert)'
  $unit.sourceType='Owner attestation (domain expert)'
  $unit.evidence=($attest -f $unit.language)
  if($unit.PSObject.Properties.Name -contains 'manualReason'){ $unit.manualReason=$null }
  $unit.checkedAt=(Get-Date -Format s)
  $logRows += [pscustomobject]@{unitId=$unit.unitId;lang=$unit.language;variant=$unit.variant;status='confirmed';source='owner attestation';at=$unit.checkedAt}
  $applied++
}
# leave a precise reason on the Portuguese xPRE units
foreach($unit in $units){
  if($unit.setCode -eq 'xPRE' -and $unit.language -eq 'Portuguese' -and $unit.status -eq 'needs-manual-review'){
    $unit | Add-Member manualReason 'Prismatic Evolutions: Additionals - owner confirmed FR/DE/IT/ES(European) but explicitly did NOT confirm Portuguese; no source found' -Force
  }
}
$units | ConvertTo-Json -Depth 4 | Set-Content "$V\units.json" -Encoding utf8
if($logRows){ $logRows | ForEach-Object{ $_ | ConvertTo-Json -Compress } | Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='xpre';completedAt=(Get-Date -Format s)} | ConvertTo-Json | Set-Content "$V\state.json" -Encoding utf8
Write-Host "xPRE units confirmed: $applied"
