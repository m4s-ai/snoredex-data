$ErrorActionPreference='Stop'
$V="C:\Users\marku\Claude\snorlax-cardmarket\verification"
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json
$jpUrl='https://bulbapedia.bulbagarden.net/wiki/XY-P_Promotional_cards_(TCG)'
$srcType='Bulbapedia (fan wiki), Japanese promo series article + Korean promo series article'

$jpText149='Japanese XY-P promo series (438 listed cards): "149/XY-P Snorlax ... Marumiya July 2015 Pokemon promotion" - a tie-in with the Japanese food manufacturer Marumiya.'
$jpText261='Japanese XY-P promo series (438 listed cards): "261/XY-P Snorlax ... Daiichi Pan September 2016 Pokemon promotion (September 1, 2016)" - a tie-in with the Japanese bakery Daiichi Pan.'
$krNote=' Distribution was a Japan-only retail campaign with no overseas equivalent. The Korean XY-P series (211 listed cards) does contain a Snorlax, but as its own entry "167/XY-P" under independent Korean numbering, which does not establish a Korean printing of this particular card.'

$claims=@(
 [pscustomobject]@{num='149'; lang='Japanese'; state='confirmed';    text=$jpText149}
 [pscustomobject]@{num='261'; lang='Japanese'; state='confirmed';    text=$jpText261}
 [pscustomobject]@{num='149'; lang='Korean';   state='contradicted'; text=$jpText149+$krNote+' User (domain expert) confirms this is a Japanese-exclusive promo.'}
 [pscustomobject]@{num='261'; lang='Korean';   state='contradicted'; text=$jpText261+$krNote+' NOTE: the user statement covered 149; the same Japan-only food-campaign reasoning is extended to 261 here.'}
)
$applied=0; $logRows=@()
foreach($claim in $claims){
  foreach($unit in $units){
    if($unit.setCode -ne 'XY-P'){ continue }
    if("$($unit.number)".Trim() -ne $claim.num){ continue }
    if($unit.language -ne $claim.lang){ continue }
    if($unit.status -in @('confirmed','contradicted')){ continue }
    $unit.status=$claim.state
    $unit.sourceUrl=$jpUrl; $unit.sourceType=$srcType; $unit.evidence=$claim.text
    $unit.checkedAt=(Get-Date -Format s)
    $logRows += [pscustomobject]@{unitId=$unit.unitId;lang=$unit.language;status=$claim.state;source=$jpUrl;evidence=$claim.text;at=$unit.checkedAt}
    $applied++
  }
}
$units | ConvertTo-Json -Depth 4 | Set-Content "$V\units.json" -Encoding utf8
if($logRows){ $logRows | ForEach-Object{ $_ | ConvertTo-Json -Compress } | Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='xyp';completedAt=(Get-Date -Format s)} | ConvertTo-Json | Set-Content "$V\state.json" -Encoding utf8
Write-Host "applied: $applied"
