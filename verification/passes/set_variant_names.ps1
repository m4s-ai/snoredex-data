$ErrorActionPreference='Stop'
$B="C:\redacted\Claude\snorlax-cardmarket"
$V="$B\verification"
$cards=Get-Content "$B\snorlax_cards.json" -Raw -Encoding utf8|ConvertFrom-Json
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json

# Named variants for the "x<SET>" special editions.
# Cardmarket exposes only an opaque -V1/-V2/-V3 slug token; these are the actual printings.
# Poke Ball / Master Ball assignment for xsv2a supplied by the user (domain knowledge);
# the downloaded scans show a tiled ball pattern on both but are too low-resolution to tell
# the two apart, so this is NOT derived from the image.
$M=@(
 [pscustomobject]@{code='xsv2a'; num='143'; v='V1'; name='Poké Ball mirror holo';   src='user'}
 [pscustomobject]@{code='xsv2a'; num='143'; v='V2'; name='Master Ball mirror holo'; src='user'}
 [pscustomobject]@{code='xJTG';  num='117'; v='V1'; name='"Journey Together" stamp (gift with purchase, Malaysia/Philippines/Singapore)'; src='Bulbapedia set list + stamp read off the downloaded scan'}
 [pscustomobject]@{code='xJTG';  num='117'; v='V2'; name='"GameStop" stamp (gift with purchase, USA/Canada)';                              src='Bulbapedia set list + stamp read off the downloaded scan'}
 [pscustomobject]@{code='xJTG';  num='117'; v='V3'; name='"EBGames" stamp (gift with purchase, Australia/New Zealand)';                     src='Bulbapedia set list + stamp read off the downloaded scan'}
 [pscustomobject]@{code='xPRE';  num='076'; v='V1'; name='"Prismatic Evolutions" stamp, Snorlax ex & Blissey ex Special Collection';        src='Bulbapedia Prismatic Evolutions set list'}
 [pscustomobject]@{code='xPRE';  num='076'; v='V2'; name='Jumbo / oversized printing, Snorlax ex & Blissey ex Special Collection';          src='Bulbapedia Prismatic Evolutions set list'}
 # xm2a carries two different mirror foils: a Poke Ball pattern and an Energy pattern
 # (a star, the colourless-energy symbol). NOTE the order is INVERTED relative to xsv2a -
 # here the Poke Ball sits on V2, not V1. Read off a 5x upscaled crop of the scans
 # (verification/zoom_variant.ps1): V2 shows an unmistakable Poke Ball with band and centre
 # button; V1 shows the star, its two upper notches being the concave angles between points.
 [pscustomobject]@{code='xm2a';  num='136'; v='V1'; name='mirror holo, colourless-energy star pattern'; src='user + read off 5x upscaled crop of the scan'}
 [pscustomobject]@{code='xm2a';  num='136'; v='V2'; name='mirror holo, Poké Ball pattern';              src='user + read off 5x upscaled crop of the scan'}
)
function NN($n){ if($null -eq $n){return ''}; $s="$n".Trim()
  if($s -match '^[A-Za-z\-]*?(\d+)$'){ return [string][int]$Matches[1] }; return $s.ToUpper() }

$c=0
foreach($r in $M){
  foreach($k in $cards.cards){
    if($k.setCode -ne $r.code){continue}
    if((NN $k.number) -ne (NN $r.num)){continue}
    if($k.variantToken -ne $r.v){continue}
    $k | Add-Member variantName $r.name -Force
    $k | Add-Member variantNameSource $r.src -Force
    $c++
  }
  foreach($u in $units){
    if($u.setCode -ne $r.code){continue}
    if((NN $u.number) -ne (NN $r.num)){continue}
    if($u.variant -ne $r.v){continue}
    $u | Add-Member variantName $r.name -Force
    $u | Add-Member variantNameSource $r.src -Force
  }
}
$cards | ConvertTo-Json -Depth 6 | Set-Content "$B\snorlax_cards.json" -Encoding utf8
$units | ConvertTo-Json -Depth 4 | Set-Content "$V\units.json" -Encoding utf8
Write-Host "variant names written to $c cards (and matching units)"
$cards.cards | Where-Object{$_.variantName} | Select-Object setCode,number,variantToken,variantName,variantNameSource | Format-Table -Auto -Wrap
