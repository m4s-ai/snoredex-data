$ErrorActionPreference='Stop'
$V="C:\redacted\Claude\snorlax-cardmarket\verification"
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json
$KR='https://bulbapedia.bulbagarden.net/wiki/Pok%C3%A9mon_in_South_Korea'
$TW='https://bulbapedia.bulbagarden.net/wiki/Pok%C3%A9mon_in_Taiwan'
$TKR='Bulbapedia (fan wiki), "Pokémon in South Korea", Trading Card Game section'
$TTW='Bulbapedia (fan wiki), "Pokémon in Taiwan", Trading Card Game section'

$QKR1='"Prior to the DP Era, only two sets of the Trading Card Game were officially printed in Korean" - Base Set (2000) and ADV Expansion Pack plus the Treecko/Torchic/Mudkip starter decks (2004).'
$QKR2='"With the release of the Diamond and Pearl sets, the Korean-language cards were released again ... however Korean sets at this time were a unique combination of existing cards, with none of the sets themselves corresponding to existing sets. It wouldn''t be until the release of the Black and White sets in Japan that Korean sets would follow a format that is on par with Japan and North American releases."'
$QTW='"Prior to the Sun & Moon era, only two sets of the Trading Card Game were officially printed in Traditional Chinese" ... "In 2019, The Pokemon Company started localizing ... The Pokemon Trading Card Game was localized in Traditional Chinese and made available in Taiwan, Hong Kong, and Macau ... in October 2019 starting with the All Stars Collection expansion."'

# Japanese-market sets published BEFORE the Traditional Chinese launch (Oct 2019).
$TW_PRE=@('PJU','G2','EC5','DP1','DP-P','LL','HSZ','HXY','XY-P','XY2','XY10','BW-P','BW7','20th','smL','sm9','sm10','SM-P')
# Korean: pre-DP era - no Korean printing at all
$KR_PRE_DP=@('PJU','G2','EC5')
# Korean: DP through HGSS - Korean sets existed but did not correspond to Japanese sets
$KR_DP_HGSS=@('DP1','LL','HSZ')

$x=0;$ev=@()
foreach($u in $units){
  if($u.status -in @('confirmed','contradicted','needs-manual-review')){continue}
  $hit=$null
  if($u.language -eq 'T-Chinese' -and $TW_PRE -contains $u.setCode){
    $hit=@($TW,$TTW,"$($u.setName) predates the Traditional Chinese launch (October 2019, All Stars Collection), so no Traditional Chinese printing of this set exists. $QTW Note: the card itself may exist in Traditional Chinese via a later catch-up set, but not as a printing of this set.")
  }
  elseif($u.language -eq 'Korean' -and $KR_PRE_DP -contains $u.setCode){
    $hit=@($KR,$TKR,"$($u.setName) predates the DP era. $QKR1 This set is not among them, so no Korean printing exists.")
  }
  elseif($u.language -eq 'Korean' -and $KR_DP_HGSS -contains $u.setCode){
    $hit=@($KR,$TKR,"$($u.setName) falls between the DP and Black & White eras, when Korean sets were unique recombinations rather than translations of Japanese sets. $QKR2 So no Korean printing of this set exists.")
  }
  if(-not $hit){continue}
  $u.status='contradicted'; $u.sourceUrl=$hit[0]; $u.sourceType=$hit[1]; $u.evidence=$hit[2]
  $u.checkedAt=(Get-Date -Format s)
  $ev+=[pscustomobject]@{unitId=$u.unitId;lang=$u.language;status='contradicted';source=$u.sourceUrl;evidence=$u.evidence;at=$u.checkedAt}
  $x++
}
$units|ConvertTo-Json -Depth 4|Set-Content "$V\units.json" -Encoding utf8
if($ev){ $ev|ForEach-Object{$_|ConvertTo-Json -Compress}|Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='market-history';completedAt=(Get-Date -Format s)}|ConvertTo-Json|Set-Content "$V\state.json" -Encoding utf8
Write-Host "contradicted from market history: $x"
$units|Group-Object status|Sort-Object Count -Desc|Format-Table Count,Name -Auto
