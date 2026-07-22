$ErrorActionPreference='Continue'
$V="C:\redacted\Claude\snorlax-cardmarket\verification"
$ua="Mozilla/5.0"
$langs=@('en','fr','de','es','it','pt','pt-br','nl','pl','ru','ja','ko','zh-tw','zh-cn','id','th')
foreach($l in $langs){
  foreach($kind in @('cards','sets')){
    $f="$V\cache\full_${kind}_$l.json"
    if(Test-Path $f){ Write-Host "cached  $kind $l"; continue }
    try{ $r=Invoke-RestMethod -Uri "https://api.tcgdex.net/v2/$l/$kind" -UserAgent $ua -TimeoutSec 120 -ErrorAction Stop
         $r | ConvertTo-Json -Depth 4 -Compress | Set-Content $f -Encoding utf8
         Write-Host ("fetched {0,-6} {1,-6} n={2}" -f $l,$kind,@($r).Count) }
    catch{ Write-Host ("ERR     {0,-6} {1,-6} {2}" -f $l,$kind,$_.Exception.Message); '[]' | Set-Content $f -Encoding utf8 }
    Start-Sleep -Milliseconds 500
  }
}
