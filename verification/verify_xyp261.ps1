$ErrorActionPreference='Stop'
$V="C:\Users\marku\Claude\snorlax-cardmarket\verification"
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json
$searchUrl='https://pokumon.com/?s=snorlax+xy'

# Validated absence, not bare absence. The source demonstrably carries Korean XY-P Snorlax
# promos - it lists "Snorlax (167/XY-P Korean Promo)" - so the fact that it lists 261 only as
# a Japanese promo is meaningful rather than a coverage gap. This is the check that was missing
# when the earlier XY-P 149 contradiction was made and had to be reverted.
$evidenceText = 'Validated absence. A collector database search for "snorlax xy" returns exactly four printings: "Snorlax (167/XY-P Korean Promo)" (Kisstick sausages promotion, 2017), "Snorlax (261/XY-P Japanese Promo)" (Daiichi Pan, September 2016), "Snorlax (149/XY-P Japanese Promo)" (Marumiya, July 2015) and "Snorlax (XY179 English Promo)" (Snorlax-GX Box). The source therefore does list Korean XY-P Snorlax promos - it carries 167 - which makes the absence of any Korean 261 meaningful rather than a gap in coverage. XY-P 261 corresponds to a different card from 149 (Bulbapedia redirects it to "Snorlax (XY Promo 179)"), so the Korean 167 does not cover it. Search: ' + $searchUrl

$changed=0; $logRows=@()
foreach($unit in $units){
  if($unit.setCode -ne 'XY-P'){ continue }
  if("$($unit.number)".Trim() -ne '261'){ continue }
  if($unit.language -ne 'Korean'){ continue }
  if($unit.status -in @('confirmed','contradicted')){ continue }
  $unit.status='contradicted'
  $unit.sourceUrl=$searchUrl
  $unit.sourceType='pokumon.com (collector card database), promo search'
  $unit.evidence=$evidenceText
  $unit.checkedAt=(Get-Date -Format s)
  $logRows += [pscustomobject]@{unitId=$unit.unitId;lang='Korean';status='contradicted';source=$searchUrl;evidence=$evidenceText;at=$unit.checkedAt}
  $changed++
}
$units | ConvertTo-Json -Depth 4 | Set-Content "$V\units.json" -Encoding utf8
if($logRows){ $logRows | ForEach-Object{ $_ | ConvertTo-Json -Compress } | Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='xyp261';completedAt=(Get-Date -Format s)} | ConvertTo-Json | Set-Content "$V\state.json" -Encoding utf8
Write-Host "contradicted: $changed"
