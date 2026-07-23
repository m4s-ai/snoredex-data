$ErrorActionPreference='Stop'
$V=Split-Path -Parent $PSScriptRoot
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json

# BUG FIX. classify_manual.ps1 used  $u.setCode -match '^x'  to detect Cardmarket
# "Additionals" sets. PowerShell's -match is CASE-INSENSITIVE, so it also caught
# XY-P, XY2, XY10 and XYPR, which are ordinary sets. Those units were parked in
# needs-manual-review and were therefore skipped by every later evidence pass.
# Correct operator is -cmatch. Release the wrongly parked units back to pending.
$realAdditionals = @('xJTG','xPRE','xsv2a','xm2a')
$released=0
foreach($unit in $units){
  if($unit.status -ne 'needs-manual-review'){ continue }
  $isAdditionals = $unit.setCode -cmatch '^x'
  $isPrizePack   = $unit.setCode -cmatch '^PPS\d'
  if($isAdditionals -or $isPrizePack){ continue }
  $unit.status='pending'
  if($unit.PSObject.Properties.Name -contains 'manualReason'){ $unit.manualReason=$null }
  $unit.checkedAt=(Get-Date -Format s)
  $released++
}
$units | ConvertTo-Json -Depth 4 | Set-Content "$V\units.json" -Encoding utf8
Write-Host "released from manual review: $released"
Write-Host ("sanity - real Additionals codes present: {0}" -f (($units|?{$_.setCode -cmatch '^x'}|Select-Object -Expand setCode -Unique) -join ', '))
$units|Group-Object status|Sort-Object Count -Desc|Format-Table Count,Name -Auto
