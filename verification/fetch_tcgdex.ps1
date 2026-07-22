$ErrorActionPreference='Continue'
$base="C:\Users\marku\Claude\snorlax-cardmarket\verification"
$cache="$base\cache"
$ua="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"
$langs=@('en','fr','de','es','it','pt','pt-br','nl','pl','ru','ja','ko','zh-tw','zh-cn','id','th')
foreach($l in $langs){
  $f="$cache\tcgdex_$l.json"
  if(Test-Path $f){ Write-Host "cached  $l"; continue }
  $all=@{}
  foreach($q in @("dexId=143","name=Snorlax")){
    try{ $r=Invoke-RestMethod -Uri "https://api.tcgdex.net/v2/$l/cards?$q" -UserAgent $ua -TimeoutSec 40 -ErrorAction Stop
         foreach($c in $r){ $all[$c.id]=$c } }
    catch{ }
    Start-Sleep -Milliseconds 400
  }
  ($all.Values) | ConvertTo-Json -Depth 5 | Set-Content $f -Encoding utf8
  Write-Host ("fetched {0,-6} cards={1}" -f $l,$all.Count)
  Start-Sleep -Milliseconds 600
}
