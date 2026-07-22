$ErrorActionPreference='Stop'
$B="C:\Users\marku\Claude\snorlax-cardmarket"
$V="$B\verification"
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json

# CORRECTION + user clarification.
# Cardmarket stock images resolve the V1/V2 split: V2 carries a "Holo Version" label, V1 does not.
#   PPS8 JTG 117 V1 = Non-Holo   PPS8 JTG 117 V2 = Holo (Cosmos)
# The user states the Non-Holo PPS8 is physically identical to the Non-Holo PPS7, but the two must
# remain distinct records. My holo photo therefore evidences ONLY the V2 (holo) printing.
$deHoloEv = 'Physical German HOLO specimen inspected from a photograph: "Hops Relaxo", KP 150, Fahigkeit "Extraportion", attack "Dynamische Presse" 140, Illustr. GOSSAN, "JTG DE 117/159", Play! Pokemon Prize Pack stamp, (c)2025. This is the holo (V2) printing. The card face does not distinguish PPS7 from PPS8; PPS8 is the owner attribution.'
$ptHoloEv = 'Portuguese HOLO printing: LigaPokemon lists this Prize Pack card with "Foil" copies under "Idiomas: Portugues", and a physical Portuguese holo specimen was inspected from a photograph ("Snorlax do Lupo", Habilidade "Boca-livre", "Compressao Dinamica" 140, "JTG PT 117/159", Play! stamp, (c)2025).'
$ptNonHoloEv = 'Portuguese NON-HOLO printing: LigaPokemon (Brazilian marketplace) lists "Snorlax do Lupo / Hop''s Snorlax (117b/90)", Play! Pokemon Prize Pack Series Eight, with "Normal" (non-foil) copies under "Idiomas: Portugues". Note: this non-holo print is physically identical to the PPS7 non-holo but is catalogued separately.'

foreach($unit in $units){
  if($unit.setCode -ne 'PPS8 JTG'){ continue }

  if($unit.variant -eq 'V2'){   # HOLO
    if($unit.language -eq 'German'){
      $unit.status='confirmed'; $unit.sourceType='Physical card, photographed holo specimen'
      $unit.sourceUrl='(physical specimen supplied by the user)'; $unit.evidence=$deHoloEv
      if($unit.PSObject.Properties.Name -contains 'manualReason'){ $unit.manualReason=$null }
    }
    elseif($unit.language -eq 'Portuguese'){
      $unit.status='confirmed'; $unit.sourceType='Marketplace listing (LigaPokemon, Foil) + photographed holo specimen'
      $unit.sourceUrl='https://www.ligapokemon.com.br/?view=cards/card&card=Hop%27s%20Snorlax%20(117b%2F90)&ed=PPPS8&num=117b'; $unit.evidence=$ptHoloEv
    }
  }
  elseif($unit.variant -eq 'V1'){   # NON-HOLO
    if($unit.language -eq 'German'){
      # Over-confirmed earlier from a holo photo. The non-holo German has no source - back to review.
      $unit.status='needs-manual-review'; $unit.sourceUrl=$null; $unit.sourceType=$null
      $unit.evidence=$null
      $unit | Add-Member manualReason 'Play! Pokemon Prize Pack, Non-Holo (V1) - only the holo (V2) German was photographed; the non-holo German has no source yet' -Force
    }
    elseif($unit.language -eq 'Portuguese'){
      # Liga lists non-foil Portuguese copies, so the non-holo is independently supported.
      $unit.status='confirmed'; $unit.sourceType='Marketplace listing (LigaPokemon, Normal/non-foil)'
      $unit.sourceUrl='https://www.ligapokemon.com.br/?view=cards/card&card=Hop%27s%20Snorlax%20(117b%2F90)&ed=PPPS8&num=117b'; $unit.evidence=$ptNonHoloEv
    }
  }
  $unit.checkedAt=(Get-Date -Format s)
}
$units | ConvertTo-Json -Depth 4 | Set-Content "$V\units.json" -Encoding utf8

# Name the variants in the main dataset
$cards=Get-Content "$B\snorlax_cards.json" -Raw -Encoding utf8|ConvertFrom-Json
foreach($c in $cards.cards){
  if($c.setCode -ne 'PPS8 JTG'){ continue }
  if($c.variantToken -eq 'V1'){ $c|Add-Member variantName 'Prize Pack Series Eight, Non-Holo (physically identical to the PPS7 Non-Holo print, catalogued separately)' -Force; $c|Add-Member variantNameSource 'user + Cardmarket stock image (no Holo label)' -Force }
  if($c.variantToken -eq 'V2'){ $c|Add-Member variantName 'Prize Pack Series Eight, Holo (Cosmos)' -Force; $c|Add-Member variantNameSource 'Cardmarket stock image ("Holo Version" label)' -Force }
}
$cards | ConvertTo-Json -Depth 6 | Set-Content "$B\snorlax_cards.json" -Encoding utf8

@{phase='pps8-variant-fix';completedAt=(Get-Date -Format s)} | ConvertTo-Json | Set-Content "$V\state.json" -Encoding utf8
Write-Host "PPS8 variant assignment corrected."
