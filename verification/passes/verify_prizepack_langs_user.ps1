$ErrorActionPreference='Stop'
$V="C:\redacted\Claude\snorlax-cardmarket\verification"
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json

# The project owner (domain expert) confirms that BOTH Prize Pack Series Seven and Eight exist,
# in ALL versions (holo and non-holo), in German, English, French, Italian, European Spanish and
# Portuguese. Cardmarket's "Spanish" is European Spanish, matching the stated scope.
# This closes the remaining Prize Pack language units. Evidence grade is expert attestation,
# corroborated for DE and PT by inspected specimens (photos) and the LigaPokemon marketplace;
# EN/FR/IT/ES rest on the owner's direct confirmation. Only units not already confirmed by a
# stronger source are touched, so photo/marketplace evidence is preserved.
$sixLangs=@('English','French','German','Italian','Spanish','Portuguese')
$attestEv='Owner (domain expert) confirms that Play! Pokemon Prize Pack Series Seven and Eight were both distributed, in all versions (holo and non-holo), across the six European languages: German, English, French, Italian, European Spanish and Portuguese. Corroboration in the dataset: Portuguese confirmed independently via LigaPokemon for both series, and German + Portuguese holo confirmed from photographed physical specimens. This unit (a non-DE/PT language) rests on the owner attestation plus the uniform per-region Prize Pack distribution the corroborated languages demonstrate.'

$applied=0; $logRows=@()
foreach($unit in $units){
  if($unit.setCode -notin @('PPS7 JTG','PPS8 JTG')){ continue }
  if($unit.language -notin $sixLangs){ continue }
  if($unit.status -eq 'confirmed'){ continue }   # keep stronger evidence already present
  $unit.status='confirmed'
  $unit.sourceUrl='(owner attestation, corroborated by LigaPokemon + photographed specimens)'
  $unit.sourceType='Owner attestation (domain expert), corroborated for DE/PT'
  $unit.evidence=$attestEv
  if($unit.PSObject.Properties.Name -contains 'manualReason'){ $unit.manualReason=$null }
  $unit.checkedAt=(Get-Date -Format s)
  $logRows += [pscustomobject]@{unitId=$unit.unitId;lang=$unit.language;status='confirmed';source='owner attestation';evidence=$attestEv;at=$unit.checkedAt}
  $applied++
}
$units | ConvertTo-Json -Depth 4 | Set-Content "$V\units.json" -Encoding utf8
if($logRows){ $logRows | ForEach-Object{ $_ | ConvertTo-Json -Compress } | Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='prizepack-user';completedAt=(Get-Date -Format s)} | ConvertTo-Json | Set-Content "$V\state.json" -Encoding utf8
Write-Host "Prize Pack units confirmed via owner attestation: $applied"
