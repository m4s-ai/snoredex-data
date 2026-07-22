$ErrorActionPreference='Stop'
$V="C:\redacted\Claude\snorlax-cardmarket\verification"
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json

# French for XY Black Star Promos 179 was already confirmed from TCGdex (xyp-XY179, "Ronflex",
# set "Promo XY"). Adding the physical specimen the user photographed as a second, independent
# source, because it also documents that the promo had a localized European printing at all -
# Bulbapedia describes the distribution only as "the English Snorlax-GX Box".
$evidenceText = 'Two independent sources. TCGdex carries this card in French as xyp-XY179, name "Ronflex", set "Promo XY". A physical French copy was inspected: title "Ronflex", NIV.20, 130 PV, Talent "Vaccin", attack "Plaquage" 50, Pokedex line "N 143 Pokemon Pionceur Taille 2,1 m Poids 460,0 kg", Illus. Ken Sugimori, (c)2016 Pokemon, card number XY179 with the black star promo symbol. This also shows the promo had a localized European printing, which the Bulbapedia release note ("in the English Snorlax-GX Box") does not convey.'

$changed=0; $logRows=@()
foreach($unit in $units){
  if($unit.setCode -ne 'XYPR'){ continue }
  if($unit.language -ne 'French'){ continue }
  $unit.sourceUrl='https://api.tcgdex.net/v2/fr/cards/xyp-XY179'
  $unit.sourceType='TCGdex API + physical specimen inspected'
  $unit.evidence=$evidenceText
  $unit.status='confirmed'
  $unit.checkedAt=(Get-Date -Format s)
  $logRows += [pscustomobject]@{unitId=$unit.unitId;lang='French';status='confirmed';source=$unit.sourceUrl;evidence=$evidenceText;at=$unit.checkedAt}
  $changed++
}
$units | ConvertTo-Json -Depth 4 | Set-Content "$V\units.json" -Encoding utf8
if($logRows){ $logRows | ForEach-Object{ $_ | ConvertTo-Json -Compress } | Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='xypr-fr';completedAt=(Get-Date -Format s)} | ConvertTo-Json | Set-Content "$V\state.json" -Encoding utf8
Write-Host "evidence enriched: $changed"
