Add-Type -AssemblyName System.Drawing
$B="C:\redacted\Claude\snorlax-cardmarket"
$out="$B\verification\zoom"
New-Item -ItemType Directory -Force -Path $out | Out-Null

# crop the lower-middle area where the mirror pattern is most visible, then upscale 5x
$targets=@(
  @{f='images\xm2a_136_Hop_s_Snorlax_V1_861744.jpg'; n='xm2a_V1'},
  @{f='images\xm2a_136_Hop_s_Snorlax_V2_861745.jpg'; n='xm2a_V2'}
)
foreach($t in $targets){
  $src=[System.Drawing.Image]::FromFile("$B\$($t.f)")
  $w=$src.Width; $h=$src.Height
  # region: horizontal middle 60%, vertical 62%-92%
  $rx=[int]($w*0.20); $rw=[int]($w*0.60)
  $ry=[int]($h*0.62); $rh=[int]($h*0.30)
  $rect=New-Object System.Drawing.Rectangle($rx,$ry,$rw,$rh)
  $crop=New-Object System.Drawing.Bitmap($rw,$rh)
  $g=[System.Drawing.Graphics]::FromImage($crop)
  $g.DrawImage($src,(New-Object System.Drawing.Rectangle(0,0,$rw,$rh)),$rect,[System.Drawing.GraphicsUnit]::Pixel)
  $g.Dispose()
  $sc=5
  $big=New-Object System.Drawing.Bitmap(($rw*$sc),($rh*$sc))
  $g2=[System.Drawing.Graphics]::FromImage($big)
  $g2.InterpolationMode=[System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
  $g2.DrawImage($crop,0,0,($rw*$sc),($rh*$sc))
  $g2.Dispose()
  $p="$out\$($t.n).png"
  $big.Save($p,[System.Drawing.Imaging.ImageFormat]::Png)
  $big.Dispose(); $crop.Dispose(); $src.Dispose()
  Write-Host "$($t.n): source ${w}x${h} -> crop ${rw}x${rh} -> $p"
}
