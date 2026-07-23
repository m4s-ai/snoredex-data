$ErrorActionPreference='Stop'
$V=Split-Path -Parent $PSScriptRoot
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json

# Physical holo specimens of the PPS8 (Play! Pokemon Prize Pack Series Eight) Hop's Snorlax
# JTG 117, photographed by the user and read off. The card face shows set number 117/159 and a
# Play! Pokemon stamp; it does NOT encode PPS7 vs PPS8 (that split only exists in marketplace
# catalogues), so the PPS8 attribution rests on the owner. Cardmarket's V1/V2 split for this
# product has no documented meaning either - both denote the same JTG 117 card - so the language
# is confirmed for both variant entries from the one inspected specimen.
$deEv = 'Physical German holo specimen inspected from a photograph: "Hops Relaxo", BASIS, KP 150, Fahigkeit "Extraportion" (your Hop''s Pokemon deal 30 more damage), attack "Dynamische Presse" 140 ("Dieses Pokemon fugt auch sich selbst 80 Schadenspunkte zu"), Pokedex line "Nr. 0143 Tagtraumer-Pokemon Grosse: 2,1 m Gewicht: 460,0 kg", Illustr. GOSSAN, set number "JTG DE 117/159", Play! Pokemon Prize Pack stamp in the artwork, (c)2025. Confirms a German Prize Pack printing. CAVEAT: the card face does not distinguish PPS7 from PPS8 (both reprint JTG 117 with a Play! stamp); the PPS8 attribution is the owner''s. Cardmarket''s V1/V2 split for this product is undocumented, so both variant entries take this specimen.'
$ptEv = 'Physical Portuguese holo specimen inspected from a photograph: "Snorlax do Lupo", BASICO, PS 150, Habilidade "Boca-livre", attack "Compressao Dinamica" 140 ("Este Pokemon tambem causa 80 pontos de dano a si mesmo"), Pokedex line "No 0143 Pokemon Dorminhoco Altura: 2,1 m Peso: 460,0 kg", Ilust. GOSSAN, set number "JTG PT 117/159", Play! Pokemon Prize Pack stamp, (c)2025. Corroborates the earlier LigaPokemon marketplace confirmation and additionally establishes the holo printing exists. Same PPS7/PPS8 and V1/V2 caveats as the German specimen.'

$deCount=0; $ptCount=0; $logRows=@()
foreach($unit in $units){
  if($unit.setCode -ne 'PPS8 JTG'){ continue }
  if($unit.language -eq 'German'){
    $unit.status='confirmed'
    $unit.sourceUrl='(physical specimen supplied by the user)'
    $unit.sourceType='Physical card, photographed holo specimen'
    $unit.evidence=$deEv
    if($unit.PSObject.Properties.Name -contains 'manualReason'){ $unit.manualReason=$null }
    $unit.checkedAt=(Get-Date -Format s)
    $logRows += [pscustomobject]@{unitId=$unit.unitId;lang='German';status='confirmed';source='photographed specimen';evidence=$deEv;at=$unit.checkedAt}
    $deCount++
  }
  elseif($unit.language -eq 'Portuguese'){
    $unit.sourceType='Marketplace listing (LigaPokemon) + photographed holo specimen'
    $unit.evidence=$ptEv
    $unit.checkedAt=(Get-Date -Format s)
    $logRows += [pscustomobject]@{unitId=$unit.unitId;lang='Portuguese';status='confirmed(enriched)';source='photographed specimen';evidence=$ptEv;at=$unit.checkedAt}
    $ptCount++
  }
}
$units | ConvertTo-Json -Depth 4 | Set-Content "$V\units.json" -Encoding utf8
if($logRows){ $logRows | ForEach-Object{ $_ | ConvertTo-Json -Compress } | Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='pps8-photos';completedAt=(Get-Date -Format s)} | ConvertTo-Json | Set-Content "$V\state.json" -Encoding utf8
Write-Host "German confirmed: $deCount ; Portuguese enriched: $ptCount"
