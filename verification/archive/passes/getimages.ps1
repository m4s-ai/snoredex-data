$ErrorActionPreference='Continue'
$base=Split-Path -Parent $PSScriptRoot
$dir="$base\images"
$cards=Get-Content "$base\_cards_stage2.json" -Raw -Encoding utf8|ConvertFrom-Json
$h=@{"Referer"="https://www.cardmarket.com/";"Accept"="image/avif,image/webp,image/apng,image/*,*/*;q=0.8";"Accept-Language"="en-US,en;q=0.9"}
$ua="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
# The extension records what the bytes are, not what the URL suggested (#34). Cardmarket serves
# PNG from .jpg URLs for 55 of these products; naming those .jpg misleads every MIME-sniffing
# consumer downstream. Format is decided after the download, from the magic bytes.
function Get-ImageExtension([string]$Path){
  $bytes=[System.IO.File]::ReadAllBytes($Path)
  if($bytes.Length -lt 8){ return $null }
  if($bytes[0] -eq 0x89 -and $bytes[1] -eq 0x50 -and $bytes[2] -eq 0x4E -and $bytes[3] -eq 0x47){ return 'png' }
  if($bytes[0] -eq 0xFF -and $bytes[1] -eq 0xD8 -and $bytes[2] -eq 0xFF){ return 'jpg' }
  return $null
}

$ok=0;$fail=@()
foreach($c in $cards){
  $sc = ($c.setCode -replace '[^A-Za-z0-9\.\-]','_')
  $num= (("$($c.number)" -replace '[^A-Za-z0-9]','_'))
  $nm = ($c.name -replace '[^A-Za-z0-9]','_')
  $vt = if($c.variantToken){"_$($c.variantToken)"}else{""}
  $id = ([uri]$c.imageUrl).Segments[-1] -replace '\.[A-Za-z0-9]+$',''
  $stem = "$sc`_$num`_$nm$vt`_$id"

  # Either extension may already be on disk from an earlier run.
  $existing = @('jpg','png') | ForEach-Object { "$dir\$stem.$_" } | Where-Object { Test-Path $_ } | Select-Object -First 1
  if($existing){ $c.imageFile = "images/" + (Split-Path $existing -Leaf); $ok++; continue }

  # Download to a temp file first: a failure must not leave something behind that the check
  # above would later mistake for a good image.
  $tmp="$dir\$stem.part"
  try{
    $r=Invoke-WebRequest -Uri $c.imageUrl -OutFile $tmp -PassThru -Headers $h -UserAgent $ua -TimeoutSec 40 -ErrorAction Stop
    $declared=[string]$r.Headers['Content-Type']
    $ext=Get-ImageExtension $tmp
    if(-not $ext){
      $fail += "$($c.imageUrl) :: not an image (Content-Type '$declared', magic bytes unrecognised)"
      Remove-Item $tmp -Force -ErrorAction SilentlyContinue
    } elseif($declared -and $declared -notmatch '^image/'){
      # Bytes look like an image but the server disagrees: worth stopping on rather than guessing.
      $fail += "$($c.imageUrl) :: Content-Type '$declared' is not an image type"
      Remove-Item $tmp -Force -ErrorAction SilentlyContinue
    } else {
      $fn="$stem.$ext"
      Move-Item $tmp "$dir\$fn" -Force
      $c.imageFile = "images/$fn"
      $ok++
    }
  }
  catch{
    $fail += "$($c.imageUrl) :: $($_.Exception.Message)"
    Remove-Item $tmp -Force -ErrorAction SilentlyContinue
  }
  Start-Sleep -Milliseconds 350
}
$cards | ConvertTo-Json -Depth 5 | Set-Content "$base\_cards_stage3.json" -Encoding utf8NoBOM
Write-Host "downloaded/present: $ok / $($cards.Count)"
if($fail){ Write-Host "FAILURES:"; $fail | Select-Object -First 20 | ForEach-Object{Write-Host $_} }
