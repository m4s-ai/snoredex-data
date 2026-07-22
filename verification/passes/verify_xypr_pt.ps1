$ErrorActionPreference='Stop'
$V="C:\Users\marku\Claude\snorlax-cardmarket\verification"
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json

# Upgrade: Portuguese for XY Black Star Promos 179 was previously recorded on owner attestation
# alone - the one unit in the set resting on an unverified statement. A photograph has now been
# supplied and read off, putting it on the same footing as the German, Italian and Spanish units.
$evidenceText = 'Physical Portuguese copy inspected from a photograph: "Snorlax", BASICO, NV.20, 130 PS, "Habilidade: Imunidade" (Este Pokemon nao pode ser afetado por nenhuma Condicao Especial), attack "Pancada Corporal" 50, Pokedex line "N 143 Pokemon Dorminhoco Alt: 2,1 m Peso: 460,0 kg", Fraqueza Fighting x2, Recuar 4, "Ilust. Ken Sugimori", (c)2016 Pokemon, card number XY179 with the black star promo symbol. This replaces the earlier owner-attestation record and completes all six Western languages for this promo from inspected specimens.'

$changed=0; $logRows=@()
foreach($unit in $units){
  if($unit.setCode -ne 'XYPR'){ continue }
  if($unit.language -ne 'Portuguese'){ continue }
  $unit.status='confirmed'
  $unit.sourceUrl='(physical specimen supplied by the user)'
  $unit.sourceType='Physical card, photographed specimen'
  $unit.evidence=$evidenceText
  $unit.checkedAt=(Get-Date -Format s)
  $logRows += [pscustomobject]@{unitId=$unit.unitId;lang='Portuguese';status='confirmed';source=$unit.sourceType;evidence=$evidenceText;at=$unit.checkedAt}
  $changed++
}
$units | ConvertTo-Json -Depth 4 | Set-Content "$V\units.json" -Encoding utf8
if($logRows){ $logRows | ForEach-Object{ $_ | ConvertTo-Json -Compress } | Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='xypr-pt';completedAt=(Get-Date -Format s)} | ConvertTo-Json | Set-Content "$V\state.json" -Encoding utf8
Write-Host "evidence upgraded: $changed"

# how many units now rest on user attestation alone?
$attest=@($units|Where-Object{$_.sourceType -like '*attestation*'})
Write-Host "units still on owner attestation alone: $($attest.Count)"
