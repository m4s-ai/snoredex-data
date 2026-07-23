$ErrorActionPreference='Continue'
$base=Split-Path -Parent $PSScriptRoot
$dir="$base\images"
$cards=Get-Content "$base\_cards_stage2.json" -Raw -Encoding utf8|ConvertFrom-Json
$h=@{"Referer"="https://www.cardmarket.com/";"Accept"="image/avif,image/webp,image/apng,image/*,*/*;q=0.8";"Accept-Language"="en-US,en;q=0.9"}
$ua="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
$ok=0;$fail=@()
foreach($c in $cards){
  $sc = ($c.setCode -replace '[^A-Za-z0-9\.\-]','_')
  $num= (("$($c.number)" -replace '[^A-Za-z0-9]','_'))
  $nm = ($c.name -replace '[^A-Za-z0-9]','_')
  $vt = if($c.variantToken){"_$($c.variantToken)"}else{""}
  $id = ([uri]$c.imageUrl).Segments[-1] -replace '\.jpg$',''
  $fn = "$sc`_$num`_$nm$vt`_$id.jpg"
  $c.imageFile = "images/$fn"
  $p="$dir\$fn"
  if(Test-Path $p){ $ok++; continue }
  try{ Invoke-WebRequest -Uri $c.imageUrl -OutFile $p -Headers $h -UserAgent $ua -TimeoutSec 40 -ErrorAction Stop; $ok++ }
  catch{ $fail += "$($c.imageUrl) :: $($_.Exception.Message)" }
  Start-Sleep -Milliseconds 350
}
$cards | ConvertTo-Json -Depth 5 | Set-Content "$base\_cards_stage3.json" -Encoding utf8
Write-Host "downloaded/present: $ok / $($cards.Count)"
if($fail){ Write-Host "FAILURES:"; $fail | Select-Object -First 20 | ForEach-Object{Write-Host $_} }
