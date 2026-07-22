$ErrorActionPreference='Stop'
$V="C:\Users\marku\Claude\snorlax-cardmarket\verification"
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json

$spUrl='https://pokumon.com/?s=snorlax+s-p'
$unpUrl='https://pokumon.com/?s=hungry+snorlax'
$krUrl='https://bulbapedia.bulbagarden.net/wiki/Pok%C3%A9mon_in_South_Korea'
$twUrl='https://bulbapedia.bulbagarden.net/wiki/Pok%C3%A9mon_in_Taiwan'

# S-P 156: validated absence. The source carries S-P Snorlax promos in six languages, including
# Korean and Chinese ones, and lists 156 only as Japanese.
$spText = 'Validated absence. A collector-database search for S-P Snorlax promos returns printings in six languages - S-P 061 (Simplified Chinese), S-P 101 (Korean), S-P 145 (Chinese), S-P 052 / S-P 100 / S-P 356 (Indonesian) - so the source demonstrably covers Korean and Chinese S-P Snorlax promos. For S-P 156 it lists only "Snorlax (156/S-P Japanese Promo)", distributed as a CoroCoro Ichiban! March 2021 issue insert. The absence of a Korean or Traditional Chinese 156 is therefore evidence, not a coverage gap. Note S-P 101 is a different card and does not cover 156. Search: ' + $spUrl

# UNP: the card predates both markets. This rests on release chronology, not on absence.
$unpText = 'The card predates both markets. "Hungry Snorlax" is an unnumbered promo from the Japanese Nintendo 64 campaign of December 1997 (reprinted with the Pokemon Song Best Collection CD, 1997). The Korean TCG did not begin until 2000, and before the DP era only Base Set and the ADV Expansion Pack were ever printed in Korean - this promo is neither. Traditional Chinese localization began only in October 2019, with just Base Set (2000) and two EX-era products before that. A collector-database search returns this card only in its original Japanese printing. Sources: ' + $krUrl + ' , ' + $twUrl + ' , ' + $unpUrl

$claims=@(
 [pscustomobject]@{code='S-P'; num='156'; lang='Korean';    url=$spUrl;  type='pokumon.com (collector card database), promo search'; text=$spText}
 [pscustomobject]@{code='S-P'; num='156'; lang='T-Chinese'; url=$spUrl;  type='pokumon.com (collector card database), promo search'; text=$spText}
 [pscustomobject]@{code='UNP'; num='';    lang='Korean';    url=$krUrl;  type='Bulbapedia market-history articles + collector database'; text=$unpText}
 [pscustomobject]@{code='UNP'; num='';    lang='T-Chinese'; url=$twUrl;  type='Bulbapedia market-history articles + collector database'; text=$unpText}
)
$changed=0; $logRows=@()
foreach($claim in $claims){
  foreach($unit in $units){
    if($unit.setCode -ne $claim.code){ continue }
    if("$($unit.number)".Trim() -ne $claim.num){ continue }
    if($unit.language -ne $claim.lang){ continue }
    if($unit.status -in @('confirmed','contradicted')){ continue }
    $unit.status='contradicted'
    $unit.sourceUrl=$claim.url; $unit.sourceType=$claim.type; $unit.evidence=$claim.text
    $unit.checkedAt=(Get-Date -Format s)
    $logRows += [pscustomobject]@{unitId=$unit.unitId;lang=$unit.language;status='contradicted';source=$claim.url;evidence=$claim.text;at=$unit.checkedAt}
    $changed++
  }
}
$units | ConvertTo-Json -Depth 4 | Set-Content "$V\units.json" -Encoding utf8
if($logRows){ $logRows | ForEach-Object{ $_ | ConvertTo-Json -Compress } | Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='promo-tail';completedAt=(Get-Date -Format s)} | ConvertTo-Json | Set-Content "$V\state.json" -Encoding utf8
Write-Host "contradicted: $changed"
