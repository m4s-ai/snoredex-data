$ErrorActionPreference='Stop'
$V="C:\redacted\Claude\snorlax-cardmarket\verification"
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json

# LigaPokemon is a Brazilian (Portuguese-market) marketplace. It confirms ONLY Portuguese for
# these Prize Pack cards. The other five languages stay in manual review.
$pps7Url='https://www.ligapokemon.com.br/?view=cards/card&card=Hop%27s%20Snorlax%20(117%2F096)&ed=PPPS7&num=117'
$pps8Url='https://www.ligapokemon.com.br/?view=cards/card&card=Hop%27s%20Snorlax%20(117b%2F90)&ed=PPPS8&num=117b'
$srcType='Marketplace listing, LigaPokemon (Brazilian/Portuguese market)'

$pps7Ev='LigaPokemon (Brazilian marketplace) lists this card as "Snorlax do Lupo / Hop''s Snorlax (117/096)", edition "Play! Pokemon Prize Pack Series Seven (2025) PPPS7", with 15 sellers, every one under the language filter "Idiomas: Portugues". Portuguese distribution of this Prize Pack card is thereby confirmed. Source: ' + $pps7Url
$pps8Ev='LigaPokemon (Brazilian marketplace) lists this card as "Snorlax do Lupo / Hop''s Snorlax (117b/90)", edition "Play! Pokemon Prize Pack Series Eight (2026) PPPS8", with 8 sellers, every one under the language filter "Idiomas: Portugues". Portuguese distribution of this Prize Pack card is thereby confirmed. Source: ' + $pps8Url

$applied=0; $logRows=@()
foreach($unit in $units){
  if($unit.language -ne 'Portuguese'){ continue }
  if($unit.status -notin @('needs-manual-review','pending')){ continue }
  $ev=$null; $url=$null
  if($unit.setCode -eq 'PPS7 JTG'){ $ev=$pps7Ev; $url=$pps7Url }
  elseif($unit.setCode -eq 'PPS8 JTG'){ $ev=$pps8Ev; $url=$pps8Url }
  else { continue }
  $unit.status='confirmed'
  $unit.sourceUrl=$url; $unit.sourceType=$srcType; $unit.evidence=$ev
  if($unit.PSObject.Properties.Name -contains 'manualReason'){ $unit.manualReason=$null }
  $unit.checkedAt=(Get-Date -Format s)
  $logRows += [pscustomobject]@{unitId=$unit.unitId;lang='Portuguese';status='confirmed';source=$url;evidence=$ev;at=$unit.checkedAt}
  $applied++
}
$units | ConvertTo-Json -Depth 4 | Set-Content "$V\units.json" -Encoding utf8
if($logRows){ $logRows | ForEach-Object{ $_ | ConvertTo-Json -Compress } | Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='liga-pt';completedAt=(Get-Date -Format s)} | ConvertTo-Json | Set-Content "$V\state.json" -Encoding utf8
Write-Host "Portuguese confirmed: $applied"
