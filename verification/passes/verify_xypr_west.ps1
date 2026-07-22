$ErrorActionPreference='Stop'
$V="C:\Users\marku\Claude\snorlax-cardmarket\verification"
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json

# XY Black Star Promos 179 in the remaining Western languages. No card database carries these:
# TCGdex has only en/fr for xyp-XY179, and the collector database lumps the West into a single
# "English Promo" row. Evidence here is physical specimens supplied by the user.
# Note the evidence grade differs - three were photographed and read off, one is owner attestation.
$photoNote = 'All three photographed copies carry card number XY179 with the black star promo symbol, "Illus. Ken Sugimori" and (c)2016 Pokemon, matching the English XY179 print. This also shows the promo was localized across Europe, which the Bulbapedia release note ("in the English Snorlax-GX Box") does not convey.'

$claims=@(
 [pscustomobject]@{lang='German'; grade='photographed specimen'
   text='Physical German copy inspected from a photograph: "Relaxo", BASIS, LV.20, 130 KP, "Fahigkeit: Immunitat" (This Pokemon cannot be affected by Special Conditions), attack "Bodyslam" 50, Pokedex line "NR. 143 Tagtraumer-Pokemon GR: 2,1 m GW: 460,0 kg", weakness Fighting x2, retreat 4. ' + $photoNote}
 [pscustomobject]@{lang='Italian'; grade='photographed specimen'
   text='Physical Italian copy inspected from a photograph: "Snorlax", BASE, LIV. 20, 130 PS, "Abilita: Immunita", attack "Corposcontro" 50, Pokedex line "N. 143 Pokemon Sonno Altezza: 2,1m Peso: 460,0kg", debolezza Fighting x2, ritirata 4. ' + $photoNote}
 [pscustomobject]@{lang='Spanish'; grade='photographed specimen'
   text='Physical Spanish copy inspected from a photograph: "Snorlax", BASICO, Niv.20, 130 PS, "Habilidad: Inmunidad", attack "Golpe Cuerpo" 50, Pokedex line "N.o 143 Pokemon Dormir Altura: 2,1 m Peso: 460,0 kg", debilidad Fighting x2, retirada 4. ' + $photoNote}
 [pscustomobject]@{lang='Portuguese'; grade='owner attestation'
   text='Owner attestation: the user states they hold a Portuguese copy of this promo. NOTE: unlike the German, Italian and Spanish units this one was NOT photographed or independently inspected - it rests on the owner statement alone. The three verified European printings make a Portuguese one highly plausible, but treat this as the weakest evidence in the set.'}
)
$applied=0; $logRows=@()
foreach($claim in $claims){
  foreach($unit in $units){
    if($unit.setCode -ne 'XYPR'){ continue }
    if($unit.language -ne $claim.lang){ continue }
    if($unit.status -in @('confirmed','contradicted')){ continue }
    $unit.status='confirmed'
    $unit.sourceUrl='(physical specimen supplied by the user)'
    $unit.sourceType='Physical card, ' + $claim.grade
    $unit.evidence=$claim.text
    $unit.checkedAt=(Get-Date -Format s)
    $logRows += [pscustomobject]@{unitId=$unit.unitId;lang=$unit.language;status='confirmed';source=$unit.sourceType;evidence=$claim.text;at=$unit.checkedAt}
    $applied++
  }
}
$units | ConvertTo-Json -Depth 4 | Set-Content "$V\units.json" -Encoding utf8
if($logRows){ $logRows | ForEach-Object{ $_ | ConvertTo-Json -Compress } | Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='xypr-west';completedAt=(Get-Date -Format s)} | ConvertTo-Json | Set-Content "$V\state.json" -Encoding utf8
Write-Host "confirmed: $applied"
