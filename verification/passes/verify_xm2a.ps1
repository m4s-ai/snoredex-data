$ErrorActionPreference='Stop'
$V=Split-Path -Parent $PSScriptRoot
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json

# MEGA Dream ex mirror-holo Additionals (Hop's Snorlax xm2a 136 - V1 energy-star, V2 Poke Ball).
# Release schedule (owner, domain expert): Japan 2025-11-28, Traditional Chinese 2025-12-05,
# Thai 2026-01-16, Korean 2026-01-23, Indonesian 2026-01-30. In Thailand and Indonesia the set
# is a main expansion numbered MA3 (not the MA2a subset). Owner confirms the mirror-holo variants
# exist in ALL four localizations (KO, TC, TH, ID). This is unlike the 151 set, where Thai and
# Indonesian booster packs carried no mirror-holo prints - here they do.
$langs=@('Korean','T-Chinese','Indonesian','Thai')
$evByLang=@{}
foreach($l in $langs){
  $evByLang[$l]="Owner (domain expert) confirms the MEGA Dream ex mirror-holo Hop's Snorlax variants exist in $l. MEGA Dream ex released in $l as part of the schedule JA 2025-11-28 / TC 2025-12-05 / TH 2026-01-16 / KO 2026-01-23 / ID 2026-01-30; in Thai and Indonesian it is a main expansion numbered MA3 rather than the MA2a subset, and unlike the 151 set those localizations DO carry the mirror-holo treatment. Cardmarket files this under xm2a (Additionals); the base m2a 136 is independently confirmed in $l."
}

$applied=0; $logRows=@()
foreach($unit in $units){
  if($unit.setCode -ne 'xm2a'){ continue }
  if($unit.language -notin $langs){ continue }
  if($unit.status -eq 'confirmed'){ continue }
  $unit.status='confirmed'
  $unit.sourceUrl='(owner attestation, domain expert; MEGA Dream ex release schedule)'
  $unit.sourceType='Owner attestation (domain expert) + set release schedule'
  $unit.evidence=$evByLang[$unit.language]
  if($unit.PSObject.Properties.Name -contains 'manualReason'){ $unit.manualReason=$null }
  $unit.checkedAt=(Get-Date -Format s)
  $logRows += [pscustomobject]@{unitId=$unit.unitId;lang=$unit.language;variant=$unit.variant;status='confirmed';source='owner attestation + release schedule';at=$unit.checkedAt}
  $applied++
}
$units | ConvertTo-Json -Depth 4 | Set-Content "$V\units.json" -Encoding utf8
if($logRows){ $logRows | ForEach-Object{ $_ | ConvertTo-Json -Compress } | Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='xm2a';completedAt=(Get-Date -Format s)} | ConvertTo-Json | Set-Content "$V\state.json" -Encoding utf8
Write-Host "xm2a mirror-holo units confirmed: $applied"
