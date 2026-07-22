$ErrorActionPreference='Stop'
$V="C:\redacted\Claude\snorlax-cardmarket\verification"
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json

# Audit for the $EV/$ev case-insensitivity bug: any resolved unit whose evidence is
# not a proper, non-trivial string.
$bad=@()
foreach($unit in $units){
  if($unit.status -notin @('confirmed','contradicted')){ continue }
  $e=$unit.evidence
  $isString = $e -is [string]
  $len = if($isString){ $e.Length } else { -1 }
  if( -not $isString -or $len -lt 20 ){
    $bad += [pscustomobject]@{
      unitId=$unit.unitId; set="$($unit.setCode) $($unit.number)"; lang=$unit.language
      status=$unit.status; type=$(if($null -eq $e){'null'}else{$e.GetType().Name}); len=$len
      sourceUrl=$unit.sourceUrl
    }
  }
}
Write-Host ("resolved units: {0}" -f @($units|?{$_.status -in @('confirmed','contradicted')}).Count)
Write-Host ("units with unusable evidence: {0}" -f $bad.Count)
if($bad.Count){ $bad | Format-Table -Auto }
$bad | ConvertTo-Json -Depth 3 | Set-Content "$V\_evidence_audit.json" -Encoding utf8
