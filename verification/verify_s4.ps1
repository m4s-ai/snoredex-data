$ErrorActionPreference='Stop'
$V="C:\redacted\Claude\snorlax-cardmarket\verification"
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json
$wikiUrl='https://bulbapedia.bulbagarden.net/wiki/Vivid_Portrayals_(ATCG)'

# s4 is a Japanese MAIN EXPANSION (Amazing Volt Tackle), not a deck product.
# The Simplified Chinese market never received translations of Japanese main sets - it received
# catch-up sets. So the Simplified Chinese printing of this card exists under a different set:
# Vivid Portrayals - Obsidian (CS2aC) 086, which is already confirmed from its ATCG set list.
# Identity is established by the shared Cardmarket cardKey "Snorlax-Gormandize-Body-Slam",
# which also covers Vivid Voltage 131. Same pattern as svLN/mP1, whose Traditional Chinese
# printing is the standalone promo SV-P 215.
$evidenceText = 'Simplified Chinese printing exists under a different set. The Simplified Chinese market receives catch-up sets rather than translations of Japanese main expansions, and this card appears there as Vivid Portrayals - Obsidian (CS2aC) 086, confirmed from the ATCG set list row "Snorlax|86, Colorless, Rare". Identity is established by the shared Cardmarket cardKey "Snorlax-Gormandize-Body-Slam", which links s4 84, Vivid Voltage 131 and CS2aC 086/142. NOTE: there is no Simplified Chinese edition of the Japanese set itself; Cardmarket files the language against the Japanese product.'

$changed=0; $logRows=@()
foreach($unit in $units){
  if($unit.setCode -ne 's4'){ continue }
  if($unit.language -ne 'S-Chinese'){ continue }
  if($unit.status -in @('confirmed','contradicted')){ continue }
  if($unit.cardKey -ne 'Snorlax-Gormandize-Body-Slam'){ Write-Host "cardKey mismatch: $($unit.cardKey)"; continue }
  $unit.status='confirmed'
  $unit.sourceUrl=$wikiUrl
  $unit.sourceType='Bulbapedia (fan wiki), Simplified Chinese (ATCG) set article, via shared card identity'
  $unit.evidence=$evidenceText
  $unit.checkedAt=(Get-Date -Format s)
  $logRows += [pscustomobject]@{unitId=$unit.unitId;lang='S-Chinese';status='confirmed';source=$wikiUrl;evidence=$evidenceText;at=$unit.checkedAt}
  $changed++
}
$units | ConvertTo-Json -Depth 4 | Set-Content "$V\units.json" -Encoding utf8
if($logRows){ $logRows | ForEach-Object{ $_ | ConvertTo-Json -Compress } | Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='s4';completedAt=(Get-Date -Format s)} | ConvertTo-Json | Set-Content "$V\state.json" -Encoding utf8
Write-Host "confirmed: $changed"
